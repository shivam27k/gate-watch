from gatewatch.store import Store


def test_events_roundtrip_and_filter(tmp_path):
    s = Store(str(tmp_path / "s.db"))
    s.add_event(100.0, "a.jpg", "car")
    s.add_event(200.0, "b.jpg", "gate")
    assert s.events_since(150.0) == [(200.0, "b.jpg", "gate")]


def test_armed_default_and_persist(tmp_path):
    p = str(tmp_path / "s.db")
    s = Store(p)
    assert s.get_armed() is True
    s.set_armed(False)
    assert Store(p).get_armed() is False


def test_last_report_date_persists(tmp_path):
    p = str(tmp_path / "s.db")
    Store(p).set_last_report_date("2026-11-23")
    assert Store(p).last_report_date() == "2026-11-23"
