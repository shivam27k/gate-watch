from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))  # India has no DST
REPORT_HOUR = 12


def build_report(events, now):
    if not events:
        return "Daily report: nothing detected in the last 24 hours."
    lines = [
        f"- {cam or 'camera'}: {datetime.fromtimestamp(ts, IST).strftime('%d %b %H:%M')}"
        for ts, _, cam in events
    ]
    n = len(events)
    word = "detection" if n == 1 else "detections"
    return f"Daily report: {n} {word} in the last 24 hours (IST).\n" + "\n".join(lines)


def report_due(now, last_sent):
    now = now.astimezone(IST)
    return now.hour >= REPORT_HOUR and last_sent != now.strftime("%Y-%m-%d")
