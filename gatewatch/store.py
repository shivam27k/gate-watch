import sqlite3


class Store:
    def __init__(self, path):
        self.path = path
        with self._c() as c:
            c.execute("CREATE TABLE IF NOT EXISTS events (ts REAL, snapshot TEXT, camera TEXT DEFAULT '')")
            c.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS members (chat_id TEXT PRIMARY KEY)")

    def _c(self):
        return sqlite3.connect(self.path, timeout=10)

    def _set(self, k, v):
        with self._c() as c:
            c.execute("INSERT OR REPLACE INTO kv VALUES (?, ?)", (k, v))

    def _get(self, k):
        with self._c() as c:
            r = c.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
        return r[0] if r else None

    def add_event(self, ts, snapshot_path, camera=""):
        with self._c() as c:
            c.execute("INSERT INTO events VALUES (?, ?, ?)", (ts, snapshot_path, camera))

    def events_since(self, ts):
        with self._c() as c:
            return [(r[0], r[1], r[2]) for r in c.execute(
                "SELECT ts, snapshot, camera FROM events WHERE ts >= ? ORDER BY ts", (ts,))]

    def get_armed(self):
        return self._get("armed") != "0"

    def set_armed(self, armed):
        self._set("armed", "1" if armed else "0")

    def last_report_date(self):
        return self._get("last_report")

    def set_last_report_date(self, d):
        self._set("last_report", d)

    def add_member(self, chat_id):
        with self._c() as c:
            c.execute("INSERT OR IGNORE INTO members VALUES (?)", (str(chat_id),))

    def remove_member(self, chat_id):
        with self._c() as c:
            c.execute("DELETE FROM members WHERE chat_id=?", (str(chat_id),))

    def members(self):
        with self._c() as c:
            return [r[0] for r in c.execute("SELECT chat_id FROM members ORDER BY rowid")]
