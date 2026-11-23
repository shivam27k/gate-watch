import logging
import time

import requests

log = logging.getLogger("gatewatch")


class Telegram:
    """`recipients` is a callable returning the chat ids that get alerts."""

    def __init__(self, token, recipients):
        self.base = f"https://api.telegram.org/bot{token}"
        self.recipients = recipients
        self.offset = 0

    def _post(self, method, **kw):
        for attempt in range(3):
            try:
                r = requests.post(f"{self.base}/{method}", timeout=20, **kw)
                if r.ok:
                    return r.json()
                log.warning("telegram %s -> HTTP %s", method, r.status_code)
            except requests.RequestException as e:
                log.warning("telegram %s failed: %s", method, type(e).__name__)  # no URL: it holds the token
            time.sleep(2 ** attempt)
        return None

    def reply(self, chat_id, text):
        return self._post("sendMessage", data={"chat_id": str(chat_id), "text": text})

    def send_text(self, text):
        for cid in self.recipients():
            self.reply(cid, text)

    def send_photo(self, path, caption):
        for cid in self.recipients():
            try:
                with open(path, "rb") as f:
                    res = self._post("sendPhoto", data={"chat_id": str(cid), "caption": caption},
                                     files={"photo": f})
            except OSError:
                res = None
            if res is None:  # photo missing or failed: still tell them
                self.reply(cid, caption)

    def poll_commands(self):
        """Returns [(chat_id, first_name, lowercased text)] for every incoming message."""
        res = self._post("getUpdates", data={"offset": self.offset, "timeout": 0})
        out = []
        for u in (res or {}).get("result", []):
            self.offset = u["update_id"] + 1
            m = u.get("message") or {}
            if m.get("text") and m.get("chat", {}).get("type") == "private":
                out.append((str(m["chat"]["id"]), m.get("from", {}).get("first_name", "someone"),
                            m["text"].strip().lower().lstrip("/")))
        return out
