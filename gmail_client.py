"""Gmail API wrapper: OAuth, fetch, send."""

import base64
import os
from email.mime.text import MIMEText
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"


def is_demo():
    return os.environ.get("WTD_DEMO") == "1" or not CREDENTIALS_FILE.exists()


def get_service():
    if is_demo():
        from mock_data import MockService
        return MockService()

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _header(headers, name):
    name_lower = name.lower()
    for h in headers:
        if h["name"].lower() == name_lower:
            return h["value"]
    return ""


def _extract_body(payload):
    if payload.get("body", {}).get("data"):
        return _decode_b64(payload["body"]["data"])
    if payload.get("parts"):
        for part in payload["parts"]:
            mime = part.get("mimeType", "")
            if mime == "text/plain" and part.get("body", {}).get("data"):
                return _decode_b64(part["body"]["data"])
        for part in payload["parts"]:
            if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
                return _decode_b64(part["body"]["data"])
        for part in payload["parts"]:
            nested = _extract_body(part)
            if nested:
                return nested
    return ""


def _decode_b64(data):
    return base64.urlsafe_b64decode(data.encode("ASCII")).decode("utf-8", errors="replace")


def _parts_have_calendar(payload):
    if payload.get("mimeType") == "text/calendar":
        return True
    for part in payload.get("parts", []) or []:
        if _parts_have_calendar(part):
            return True
    return False


def _has_attachments(payload):
    for part in payload.get("parts", []) or []:
        if part.get("filename"):
            return True
        if _has_attachments(part):
            return True
    return False


def get_profile_email(service):
    if hasattr(service, "get_email"):
        return service.get_email()
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "")


def list_unread(service, max_results=50):
    if hasattr(service, "get_messages"):
        return service.get_messages()
    me_email = get_profile_email(service)
    resp = (
        service.users()
        .messages()
        .list(userId="me", q="in:inbox is:unread", maxResults=max_results)
        .execute()
    )
    ids = [m["id"] for m in resp.get("messages", [])]

    messages = []
    for mid in ids:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=mid, format="full")
            .execute()
        )
        payload = msg.get("payload", {})
        headers = payload.get("headers", [])
        body = _extract_body(payload)
        messages.append({
            "id": msg["id"],
            "thread_id": msg["threadId"],
            "from": _header(headers, "From"),
            "to": _header(headers, "To"),
            "cc": _header(headers, "Cc"),
            "subject": _header(headers, "Subject"),
            "date": _header(headers, "Date"),
            "snippet": msg.get("snippet", ""),
            "body": body,
            "message_id_header": _header(headers, "Message-ID"),
            "references": _header(headers, "References"),
            "list_unsubscribe": _header(headers, "List-Unsubscribe"),
            "labels": msg.get("labelIds", []),
            "has_attachments": _has_attachments(payload),
            "is_calendar": _parts_have_calendar(payload),
            "me_email": me_email,
        })
    return messages


def get_thread(service, thread_id):
    if hasattr(service, "get_messages"):
        for msg in service.get_messages():
            if msg["thread_id"] == thread_id:
                return [{
                    "from": msg["from"],
                    "to": msg["to"],
                    "subject": msg["subject"],
                    "date": msg["date"],
                    "body": msg["body"],
                }]
        return []
    thread = service.users().threads().get(userId="me", id=thread_id, format="full").execute()
    out = []
    for msg in thread.get("messages", []):
        payload = msg.get("payload", {})
        headers = payload.get("headers", [])
        out.append({
            "from": _header(headers, "From"),
            "to": _header(headers, "To"),
            "subject": _header(headers, "Subject"),
            "date": _header(headers, "Date"),
            "body": _extract_body(payload),
        })
    return out


def send_reply(service, thread_id, to, subject, body, in_reply_to, references):
    if hasattr(service, "get_messages"):
        print(f"[DEMO] Would send to {to}: {body[:80]}...")
        return {"id": "demo-sent", "threadId": thread_id}
    msg = MIMEText(body)
    msg["To"] = to
    msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = (references + " " + in_reply_to).strip() if references else in_reply_to

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return (
        service.users()
        .messages()
        .send(userId="me", body={"raw": raw, "threadId": thread_id})
        .execute()
    )


def mark_read(service, message_id):
    if hasattr(service, "get_messages"):
        return {"id": message_id}
    return (
        service.users()
        .messages()
        .modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]})
        .execute()
    )
