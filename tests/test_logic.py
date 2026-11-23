from gatewatch.logic import Trigger, bottom_center, point_in_polygon, rtsp_url

SQUARE = [(0, 0), (10, 0), (10, 10), (0, 10)]


def test_polygon_inside_and_outside():
    assert point_in_polygon((5, 5), SQUARE)
    assert not point_in_polygon((15, 5), SQUARE)


def test_bottom_center():
    assert bottom_center((0, 0, 10, 20)) == (5, 20)


def test_trigger_needs_three_consecutive():
    t = Trigger(frames_needed=3, cooldown_s=120)
    assert [t.update(True, 0), t.update(True, 1), t.update(True, 2)] == [False, False, True]


def test_trigger_resets_on_gap():
    t = Trigger(3, 120)
    assert [t.update(True, 0), t.update(True, 1), t.update(False, 2), t.update(True, 3)] == [False] * 4


def test_trigger_cooldown():
    t = Trigger(3, 120)
    for i in range(3):
        t.update(True, i)
    assert not any(t.update(True, 3 + i) for i in range(50))  # still within 120 s
    assert any(t.update(True, 121 + i) for i in range(3))


def test_dwell_requires_continuous_presence_with_gap_tolerance():
    t = Trigger(frames_needed=3, cooldown_s=120, dwell_s=5, gap_s=2)
    assert not any(t.update(True, i * 0.5) for i in range(10))      # 0..4.5 s: too short
    assert t.update(True, 5.0) is True                              # 5 s in zone
    t2 = Trigger(3, 120, dwell_s=5, gap_s=2)
    seq = [t2.update(i != 6, i * 0.5) for i in range(12)]           # one missed frame at 3 s
    assert seq[-2] is True or seq[-1] is True


def test_dwell_resets_after_long_gap():
    t = Trigger(3, 120, dwell_s=5, gap_s=2)
    for i in range(6):
        t.update(True, i * 0.5)          # present 0..2.5 s
    t.update(False, 6.0)                 # gone > 2 s
    assert not any(t.update(True, 7 + i * 0.5) for i in range(8))  # restarts: <5 s again


def test_rtsp_url_encodes_password():
    u = rtsp_url("h", "admin", "p@ss+word", 2)
    assert "p%40ss%2Bword" in u and u.endswith("channel=2&subtype=1")
