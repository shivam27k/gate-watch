from datetime import datetime, timedelta, timezone

from gatewatch.report import build_report, report_due

IST = timezone(timedelta(hours=5, minutes=30))


def at(h, m, day=23):
    return datetime(2026, 11, day, h, m, tzinfo=IST)


def test_report_nothing():
    assert "nothing detected" in build_report([], at(12, 0)).lower()


def test_report_counts_and_times_per_camera():
    ev = [(at(22, 40, 22).timestamp(), "b.jpg", "car"), (at(3, 15, 23).timestamp(), "a.jpg", "gate")]
    txt = build_report(ev, at(12, 0))
    assert "2 detections" in txt and "car" in txt and "22:40" in txt and "gate" in txt and "03:15" in txt


def test_report_due_rules():
    assert not report_due(at(11, 59), None)
    assert report_due(at(12, 0), None)
    assert not report_due(at(13, 0), "2026-11-23")
    assert report_due(at(12, 0, 24), "2026-11-23")
    assert report_due(at(14, 0), None)  # restarted after noon, not yet sent today
