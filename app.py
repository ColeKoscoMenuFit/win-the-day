"""Win The Day Mail — local Gmail dashboard."""

import re

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

import ai_drafter
import categorizer
import gmail_client

load_dotenv()

app = Flask(__name__)
_service = None
_cached_emails = None
_cached_categorized = None


def service():
    global _service
    if _service is None:
        _service = gmail_client.get_service()
    return _service


def _email_addr(header_value):
    if not header_value:
        return ""
    m = re.search(r"<([^>]+)>", header_value)
    return m.group(1).strip() if m else header_value.strip()


def _serialize(msg):
    return {
        "id": msg["id"],
        "thread_id": msg["thread_id"],
        "from": msg.get("from", ""),
        "from_addr": _email_addr(msg.get("from", "")),
        "subject": msg.get("subject", "") or "(no subject)",
        "snippet": msg.get("snippet", ""),
        "date": msg.get("date", ""),
        "has_attachments": msg.get("has_attachments", False),
        "is_calendar": msg.get("is_calendar", False),
    }


def _refresh():
    global _cached_emails, _cached_categorized
    _cached_emails = gmail_client.list_unread(service())
    _cached_categorized = categorizer.categorize(_cached_emails)
    return _cached_categorized


def _find(thread_id):
    if _cached_emails is None:
        _refresh()
    for msg in _cached_emails:
        if msg["thread_id"] == thread_id:
            return msg
    return None


@app.route("/")
def index():
    try:
        me_email = gmail_client.get_profile_email(service())
    except Exception as e:
        return f"<h1>Setup error</h1><pre>{e}</pre>", 500
    return render_template("dashboard.html", account=me_email)


@app.route("/api/emails")
def api_emails():
    categorized = _refresh() if _cached_categorized is None else _cached_categorized
    return jsonify({
        key: [_serialize(m) for m in msgs]
        for key, msgs in categorized.items()
    })


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    ai_drafter.clear_cache()
    categorized = _refresh()
    return jsonify({
        key: [_serialize(m) for m in msgs]
        for key, msgs in categorized.items()
    })


@app.route("/api/thread/<thread_id>")
def api_thread(thread_id):
    msg = _find(thread_id)
    if not msg:
        return jsonify({"error": "not found"}), 404
    thread = gmail_client.get_thread(service(), thread_id)
    return jsonify({
        "thread_id": thread_id,
        "from": msg["from"],
        "from_addr": _email_addr(msg["from"]),
        "subject": msg["subject"],
        "body": msg.get("body", ""),
        "thread": thread,
    })


@app.route("/api/draft/<thread_id>")
def api_draft(thread_id):
    msg = _find(thread_id)
    if not msg:
        return jsonify({"error": "not found"}), 404
    thread = gmail_client.get_thread(service(), thread_id)
    draft = ai_drafter.generate_draft(thread_id, thread, msg.get("me_email", ""))
    return jsonify({"thread_id": thread_id, "draft": draft})


@app.route("/api/draft/<thread_id>/regenerate", methods=["POST"])
def api_regenerate(thread_id):
    msg = _find(thread_id)
    if not msg:
        return jsonify({"error": "not found"}), 404
    thread = gmail_client.get_thread(service(), thread_id)
    draft = ai_drafter.generate_draft(thread_id, thread, msg.get("me_email", ""), force=True)
    return jsonify({"thread_id": thread_id, "draft": draft})


@app.route("/api/send", methods=["POST"])
def api_send():
    data = request.get_json(force=True)
    thread_id = data.get("thread_id")
    body = (data.get("body") or "").strip()
    if not thread_id or not body:
        return jsonify({"error": "thread_id and body are required"}), 400

    msg = _find(thread_id)
    if not msg:
        return jsonify({"error": "thread not found"}), 404

    to = _email_addr(msg["from"])
    subject = msg["subject"] or ""
    in_reply_to = msg.get("message_id_header", "")
    references = msg.get("references", "")

    gmail_client.send_reply(
        service(), thread_id, to, subject, body, in_reply_to, references
    )
    try:
        gmail_client.mark_read(service(), msg["id"])
    except Exception:
        pass

    global _cached_emails, _cached_categorized
    if _cached_emails:
        _cached_emails = [m for m in _cached_emails if m["thread_id"] != thread_id]
        _cached_categorized = categorizer.categorize(_cached_emails)

    return jsonify({"ok": True})


if __name__ == "__main__":
    print("Starting Gmail OAuth (browser will open if first run)...")
    service()
    print("Win The Day Mail running at http://localhost:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
