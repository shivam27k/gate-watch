from urllib.parse import quote


def point_in_polygon(pt, poly):
    """Ray casting."""
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def bottom_center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, y2)


class Trigger:
    """Fires once a person has been in the zone for `frames_needed` consecutive frames
    and for at least `dwell_s` seconds (brief misses up to `gap_s` don't reset the
    dwell), then stays quiet for `cooldown_s` seconds."""

    def __init__(self, frames_needed=3, cooldown_s=120, dwell_s=0, gap_s=0):
        self.frames_needed = frames_needed
        self.cooldown_s = cooldown_s
        self.dwell_s = dwell_s
        self.gap_s = gap_s
        self._streak = 0
        self._since = None
        self._last_seen = None
        self._last_fired = None

    def update(self, in_zone, now):
        if not in_zone:
            if self._last_seen is None or now - self._last_seen > self.gap_s:
                self._streak = 0
                self._since = None
            return False
        if self._since is None:
            self._since = now
        self._last_seen = now
        self._streak += 1
        if self._streak < self.frames_needed or now - self._since < self.dwell_s:
            return False
        if self._last_fired is not None and now - self._last_fired < self.cooldown_s:
            return False
        self._last_fired = now
        self._streak = 0
        self._since = None
        return True


def rtsp_url(host, user, password, channel, subtype=1):
    return (
        f"rtsp://{quote(user, safe='')}:{quote(password, safe='')}@{host}:554"
        f"/cam/realmonitor?channel={channel}&subtype={subtype}"
    )
