#!/usr/bin/env python3
# chat_cli.py - simple interactive console client for Chatbi /chat endpoint
# Usage:
#   python chat_cli.py [--sid YOUR_SESSION_ID] [--url http://127.0.0.1:8000]
#
# Notes:
# - Keeps a persistent session id so the backend can use Redis history/slots.
# - Type /exit or Ctrl+C to quit.
# - Type /sid to print the current session id.
# - Type /lang it|en|fr to send a one-off language hint (prepends "Please reply in <lang>")
# - UTF-8 safe printing on Windows.

import argparse
import os
import uuid
import requests

DEFAULT_URL = os.environ.get("CHATBI_URL", "http://127.0.0.1:8000")
CHAT_EP = "/chat"


def ensure_utf8_console():
    """Try to force UTF-8 output on Windows consoles."""
    try:
        if os.name == "nt":
            import ctypes

            # Set output mode to UTF-8 code page 65001
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass


def parse_args():
    ap = argparse.ArgumentParser(description="Interactive Chatbi CLI")
    ap.add_argument("--sid", help="Session id (default random UUID)")
    ap.add_argument("--url", default=DEFAULT_URL, help="Base URL, default %(default)s")
    return ap.parse_args()


def post_chat(base_url: str, sid: str, message: str) -> dict:
    url = base_url.rstrip("/") + CHAT_EP
    headers = {"Content-Type": "application/json", "X-Session-Id": sid}
    payload = {"message": message}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def format_reply(obj: dict) -> str:
    if not isinstance(obj, dict):
        return str(obj)
    if "error" in obj:
        return f"[error] {obj['error']}"
    reply = obj.get("reply") or obj.get("answer") or obj.get("text") or ""
    intent = obj.get("intent")
    # Print first citation compactly if present
    cite = ""
    try:
        c0 = (obj.get("citations") or [])[0]
        if c0:
            q = c0.get("question") or ""
            coll = (c0.get("meta") or {}).get("collection") or ""
            cite = f"\n— source: {q} [{coll}]"
    except Exception:
        pass
    intent_tag = f" ({intent})" if intent else ""
    return f"{reply}{intent_tag}{cite}"


def main():
    ensure_utf8_console()
    args = parse_args()
    sid = args.sid or str(uuid.uuid4())
    base_url = args.url

    print(f"Chatbi CLI ready. Base URL: {base_url}  |  session: {sid}")
    print("Type your message and press Enter. Commands: /exit, /sid, /lang <code>")
    lang_hint = None

    while True:
        try:
            msg = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break

        if not msg:
            continue
        if msg.lower() in ("/exit", "/quit"):
            print("bye")
            break
        if msg.lower() == "/sid":
            print(f"[session] {sid}")
            continue
        if msg.lower().startswith("/lang "):
            parts = msg.split()
            if len(parts) == 2:
                lang_hint = parts[1].strip().lower()
                print(f"[lang] set one-off hint to: {lang_hint}")
            else:
                print("usage: /lang it|en|fr|...")
            continue

        send_text = msg
        if lang_hint:
            # minimal, non-invasive hint
            send_text = f"{msg}\n\n(Per favore rispondi in {lang_hint} / Please reply in {lang_hint})"
            lang_hint = None

        resp = post_chat(base_url, sid, send_text)
        print(format_reply(resp))


if __name__ == "__main__":
    main()
