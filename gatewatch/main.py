import logging
import os
import threading
import time
from datetime import datetime

from .logic import Trigger, bottom_center, point_in_polygon
from .report import IST, build_report, report_due

log = logging.getLogger("gatewatch")
STALL_ALERT_S = 300  # tell everyone if a camera gives no frames for this long


def _safe(fn, *a):
    try:
        fn(*a)
    except Exception:
        log.exception("send failed")


def housekeeping(tg, store, now, state, owner_id):
    """Commands from chats and the daily report. Called from one thread only."""
    ts = now.timestamp()
    try:
        if state.get("last_poll") is None or ts - state["last_poll"] >= 5:
            state["last_poll"] = ts
            allowed = {str(owner_id), *store.members()}
            for cid, name, text in tg.poll_commands():
                cid = str(cid)
                parts = text.split()
                cmd = parts[0] if parts else ""
                if cid not in allowed:
                    tg.reply(cid, f"Not authorized yet. Your ID is {cid}. I've asked the owner to approve you.")
                    asked = state.setdefault("asked", set())
                    if cid not in asked:
                        asked.add(cid)
                        tg.reply(owner_id, f"{name} ({cid}) wants access. Reply 'allow {cid}' to approve.")
                elif cmd in ("arm", "disarm"):
                    store.set_armed(cmd == "arm")
                    tg.send_text(f"{'Armed' if cmd == 'arm' else 'Disarmed'} by {name}."
                                 + ("" if cmd == "arm" else " No alerts until someone sends 'arm'."))
                elif cmd == "status":
                    n = len(store.events_since(ts - 86400))
                    tg.reply(cid, f"{'Armed' if store.get_armed() else 'Disarmed'}. {n} detections in the last 24h.")
                elif cid == str(owner_id) and cmd == "allow" and len(parts) > 1:
                    store.add_member(parts[1])
                    tg.reply(cid, f"Added {parts[1]}.")
                    tg.reply(parts[1], "You now have access. Commands: arm, disarm, status.")
                elif cid == str(owner_id) and cmd == "remove" and len(parts) > 1:
                    store.remove_member(parts[1])
                    tg.reply(cid, f"Removed {parts[1]}.")
                elif cid == str(owner_id) and cmd == "members":
                    tg.reply(cid, "Members: " + (", ".join(store.members()) or "none besides you"))
        if report_due(now, store.last_report_date()):
            tg.send_text(build_report(store.events_since(ts - 86400), now))
            store.set_last_report_date(now.astimezone(IST).strftime("%Y-%m-%d"))
    except Exception:
        log.exception("housekeeping failed")


def watch(stream, detector, tg, store, zone, clock, save_snapshot, name="camera", dwell_s=0,
          snapshot_dir="snapshots", max_iters=None, sleep=time.sleep):
    trigger = Trigger(3, 120, dwell_s=dwell_s, gap_s=2 if dwell_s else 0)
    last_frame_at = None
    stall_reported = False
    i = 0
    while max_iters is None or i < max_iters:
        i += 1
        now = clock()
        ts = now.timestamp()
        try:
            frame = stream.read()
        except Exception:
            log.exception("%s: stream read failed", name)
            frame = None
        if frame is None:
            if last_frame_at is None:
                last_frame_at = ts
            if ts - last_frame_at >= STALL_ALERT_S and not stall_reported:
                stall_reported = True
                _safe(tg.send_text, f"Camera '{name}' has been unreachable for 5 minutes.")
            sleep(0.5)
            continue
        last_frame_at = ts
        if stall_reported:
            stall_reported = False
            _safe(tg.send_text, f"Camera '{name}' is back.")

        try:
            boxes = detector.person_boxes(frame)
        except Exception:
            log.exception("%s: detector failed", name)
            sleep(0.5)
            continue
        in_zone = [b for b in boxes if point_in_polygon(bottom_center(b), zone)]
        if trigger.update(bool(in_zone) and store.get_armed(), ts):
            path = os.path.join(snapshot_dir, f"{name}_{int(ts)}.jpg")
            try:
                save_snapshot(frame, in_zone, zone, path)
            except Exception:
                log.exception("%s: snapshot failed", name)
            store.add_event(ts, path, name)
            _safe(tg.send_photo, path,
                  f"Person detected at {name} — {now.astimezone(IST).strftime('%H:%M:%S')}")
        sleep(0.5)


def _camera_thread(cam, cfg, detector, tg, store, save_snapshot):
    from .logic import rtsp_url
    from .stream import Stream
    # "url" lets non-Dahua cameras supply any full RTSP URL; otherwise use the Dahua/CP Plus pattern.
    url = cam.get("url") or rtsp_url(cfg.nvr_host, cfg.nvr_user, cfg.nvr_pass, cam["channel"])
    stream = Stream(url)
    frame = None
    while frame is None:
        frame = stream.read()
        time.sleep(0.5)
    h, w = frame.shape[:2]
    zone = [(x * w, y * h) for x, y in cam["zone"]]
    watch(stream, detector, tg, store, zone, lambda: datetime.now(IST), save_snapshot,
          name=cam["name"], dwell_s=cam.get("dwell_s", 0), snapshot_dir=cfg.snapshot_dir)


def main():
    import json

    from .config import Config
    from .detector import Detector, save_snapshot
    from .store import Store
    from .telegram import Telegram

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = Config.from_env()
    os.makedirs(cfg.snapshot_dir, exist_ok=True)
    cams = json.load(open(cfg.cameras_file))
    store = Store(cfg.db_path)
    tg = Telegram(cfg.tg_token, lambda: [cfg.tg_chat_id, *store.members()])
    detector = Detector()
    for cam in cams:
        threading.Thread(target=_camera_thread, args=(cam, cfg, detector, tg, store, save_snapshot),
                         daemon=True).start()
    tg.send_text("Watch started for: " + ", ".join(c["name"] for c in cams)
                 + ("" if store.get_armed() else " (currently disarmed)"))
    state = {}
    while True:
        housekeeping(tg, store, datetime.now(IST), state, cfg.tg_chat_id)
        time.sleep(1)


if __name__ == "__main__":
    main()
