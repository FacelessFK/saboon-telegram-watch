#!/usr/bin/env python3
# Read-only watcher: polls saboon.net/api/finders and sends a Telegram message
# when the treasure-hunt status changes. It never touches the hall or the vault.
import json
import os
import sys
import urllib.parse
import urllib.request

FINDERS_URL = "https://saboon.net/api/finders"
SITE_URL = "https://saboon.net/"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
UA = "saboon-round-watch"

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(n):
    return str(n).translate(FA_DIGITS)


def fetch_finders():
    # FINDERS_FILE lets the logic be tested against a saved response
    path = os.environ.get("FINDERS_FILE")
    if path:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    req = urllib.request.Request(FINDERS_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def snapshot(data):
    ended = data.get("ended") or {}
    return {
        "open": bool(data.get("open")),
        "paused": data.get("paused") or None,
        "round": data.get("round"),
        "ended": ended.get("text"),
        "seats": sorted("%s|%s" % (r.get("round"), r.get("seat")) for r in data.get("rows", [])),
    }


def describe_open(data):
    rnd = data.get("round")
    if data.get("weekly"):
        head = "🔔 %s شروع شد" % (data.get("challenge") or "چالش هفتگی صابون")
    else:
        head = "🔔 دور %s گنج صابون شروع شد" % fa(rnd or "تازه")
    lines = [head]
    total, prize = data.get("total"), data.get("prize")
    if total and prize:
        lines.append("%s جایزهٔ %s دلاری" % (fa(total), fa(prize)))
    elif total:
        lines.append("%s جایزه" % fa(total))
    if data.get("ends_at"):
        lines.append("پایان دور: %s" % data["ends_at"])
    lines.append(SITE_URL)
    return "\n".join(lines)


def messages_for(old, new, data):
    """Return the Telegram messages for the change from old to new."""
    msgs = []
    if new["open"] and (not old or not old["open"] or old["round"] != new["round"]):
        msgs.append(describe_open(data))
    if new["paused"] and (not old or old["paused"] != new["paused"]):
        msgs.append("⏸ دور %s گنج صابون متوقف شد:\n%s" % (fa(new["round"] or ""), new["paused"]))
    if old is None:
        return msgs

    if old["open"] and not new["open"] and not new["paused"]:
        msgs.append("دور گنج صابون بسته شد.")
    if new["ended"] and new["ended"] != old["ended"]:
        msgs.append(new["ended"])

    known = set(old["seats"])
    for row in data.get("rows", []):
        if "%s|%s" % (row.get("round"), row.get("seat")) in known:
            continue
        msgs.append("🏆 یابندهٔ تازه در دور %s: %s (جایزهٔ %s از %s)" % (
            fa(row.get("round")), row.get("name"), fa(row.get("seat")), fa(row.get("of"))))
    return msgs


def send_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if os.environ.get("DRY_RUN") or not token or not chat:
        print("[dry run] would send:\n" + text + "\n")
        return
    body = urllib.parse.urlencode({
        "chat_id": chat, "text": text, "disable_web_page_preview": "true",
    }).encode()
    url = "https://api.telegram.org/bot%s/sendMessage" % token
    with urllib.request.urlopen(urllib.request.Request(url, data=body), timeout=20) as r:
        if not json.load(r).get("ok"):
            raise RuntimeError("telegram rejected the message")


def main():
    if "--test" in sys.argv:
        send_telegram("✅ ناظر صابون وصل است و پیام‌ها به این‌جا می‌رسد.")
        return 0

    try:
        data = fetch_finders()
    except Exception as e:  # a missed tick is harmless; the next run retries
        print("fetch failed: %r" % (e,), file=sys.stderr)
        return 0

    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        old = None

    new = snapshot(data)
    for text in messages_for(old, new, data):
        send_telegram(text)

    # saved only after sending, so a failed send is retried next run
    if new != old:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(new, f, ensure_ascii=False, indent=1)
        print("state changed")
    else:
        print("no change")
    return 0


if __name__ == "__main__":
    sys.exit(main())
