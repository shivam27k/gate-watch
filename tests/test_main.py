from datetime import datetime, timedelta, timezone

from gatewatch.main import housekeeping, watch
from gatewatch.store import Store

IST = timezone(timedelta(hours=5, minutes=30))
ZONE = [(0, 0), (100, 0), (100, 100), (0, 100)]
IN_BOX = (40, 20, 60, 80)    # bottom-center (50, 80) inside
OUT_BOX = (240, 20, 260, 80)


class FakeTG:
    def __init__(self, cmds=None, fail=False):
        self.photos, self.texts, self.cmds, self.fail = [], [], list(cmds or []), fail
        self.replies = []

    def reply(self, chat_id, text):
        self.replies.append((str(chat_id), text))

    def send_photo(self, path, caption):
        if self.fail:
            raise RuntimeError("net down")
        self.photos.append(caption)

    def send_text(self, text):
        self.texts.append(text)

    def poll_commands(self):
        out, self.cmds = self.cmds, []
        return out


class FakeStream:
    def __init__(self, frames):
        self.frames = list(frames)

    def read(self):
        f = self.frames.pop(0)
        if isinstance(f, Exception):
            raise f
        return f


class FakeDet:
    def person_boxes(self, frame):
        return [frame] if frame else []


def make_clock(start=None, step=0.5):
    t = [start or datetime(2026, 11, 23, 3, 0, tzinfo=IST)]

    def clock():
        t[0] += timedelta(seconds=step)
        return t[0]
    return clock


def go(tmp_path, frames, tg=None, armed=True, name="gate", dwell_s=0, **kw):
    store = Store(str(tmp_path / "s.db"))
    store.set_armed(armed)
    tg = tg or FakeTG()
    watch(FakeStream(frames), FakeDet(), tg, store, ZONE, make_clock(**kw), lambda *a: None,
          name=name, dwell_s=dwell_s, max_iters=len(frames), sleep=lambda s: None)
    return tg, store


def test_three_in_zone_frames_alert_once(tmp_path):
    tg, store = go(tmp_path, [IN_BOX] * 6)
    assert len(tg.photos) == 1 and "Person detected at gate" in tg.photos[0]
    assert [e[2] for e in store.events_since(0)] == ["gate"]


def test_outside_zone_no_alert(tmp_path):
    tg, _ = go(tmp_path, [OUT_BOX] * 6)
    assert tg.photos == []


def test_stream_error_does_not_stop_loop(tmp_path):
    tg, _ = go(tmp_path, [IN_BOX, RuntimeError("drop"), IN_BOX, IN_BOX, IN_BOX])
    assert len(tg.photos) == 1


def test_disarmed_no_alert(tmp_path):
    tg, _ = go(tmp_path, [IN_BOX] * 6, armed=False)
    assert tg.photos == []


def test_telegram_failure_still_logs_event(tmp_path):
    tg, store = go(tmp_path, [IN_BOX] * 4, tg=FakeTG(fail=True))
    assert len(store.events_since(0)) == 1


def test_car_dwell_needs_five_seconds(tmp_path):
    # 0.5 s per frame: 8 frames ~ 4 s -> no alert; 14 frames ~ 7 s -> alert
    tg, _ = go(tmp_path, [IN_BOX] * 8, name="car", dwell_s=5)
    assert tg.photos == []
    tg, _ = go(tmp_path, [IN_BOX] * 14, name="car", dwell_s=5)
    assert len(tg.photos) == 1 and "car" in tg.photos[0]


NOW = datetime(2026, 11, 23, 3, 0, tzinfo=IST)


def test_owner_can_disarm(tmp_path):
    store = Store(str(tmp_path / "s.db"))
    tg = FakeTG(cmds=[("1", "Alice", "disarm")])
    housekeeping(tg, store, NOW, {}, "1")
    assert store.get_armed() is False and "Disarmed" in tg.texts[0]


def test_stranger_is_refused_and_owner_notified_once(tmp_path):
    store = Store(str(tmp_path / "s.db"))
    st = {}
    tg = FakeTG(cmds=[("9", "Bob", "disarm"), ("9", "Bob", "status")])
    housekeeping(tg, store, NOW, st, "1")
    assert store.get_armed() is True
    assert sum("Not authorized" in t for c, t in tg.replies if c == "9") == 2
    assert [t for c, t in tg.replies if c == "1"] == ["Bob (9) wants access. Reply 'allow 9' to approve."]


def test_owner_approves_family_member_who_can_then_use_bot(tmp_path):
    store = Store(str(tmp_path / "s.db"))
    st = {}
    housekeeping(FakeTG(cmds=[("1", "Alice", "allow 9")]), store, NOW, st, "1")
    assert store.members() == ["9"]
    tg = FakeTG(cmds=[("9", "Bob", "status")])
    housekeeping(tg, store, NOW + timedelta(seconds=10), st, "1")
    assert any(c == "9" and "Armed" in t for c, t in tg.replies)


def test_family_member_cannot_approve_others(tmp_path):
    store = Store(str(tmp_path / "s.db"))
    store.add_member("9")
    housekeeping(FakeTG(cmds=[("9", "Bob", "allow 5")]), store, NOW, {}, "1")
    assert store.members() == ["9"]


def test_daily_report_sent_once(tmp_path):
    store = Store(str(tmp_path / "s.db"))
    tg = FakeTG()
    st = {}
    noon = datetime(2026, 11, 23, 12, 0, tzinfo=IST)
    housekeeping(tg, store, noon, st, "1")
    housekeeping(tg, store, noon + timedelta(seconds=30), st, "1")
    assert sum("Daily report" in t for t in tg.texts) == 1
