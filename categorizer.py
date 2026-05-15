"""Sort emails into Needs Reply / Action / FYI / Newsletters."""

import re

NEWSLETTER_DOMAINS = (
    "mailchimp", "substack", "sendgrid", "mailgun", "marketo", "hubspot",
    "constantcontact", "campaign-archive", "convertkit", "beehiiv",
    "list-manage", "amazonses", "sparkpost", "klaviyo",
)

ACTION_PATTERN = re.compile(
    r"\b(deadline|action required|please review|due (by|on)|rsvp|"
    r"sign (this|the|now)|approve|confirm|please complete|response needed|"
    r"reply by|by (eod|end of day|end of week)|urgent)\b",
    re.IGNORECASE,
)

SECTIONS = ("needs_reply", "action", "fyi", "newsletters")


def _email_addr(header_value):
    if not header_value:
        return ""
    m = re.search(r"<([^>]+)>", header_value)
    if m:
        return m.group(1).lower().strip()
    return header_value.lower().strip()


def _is_newsletter(msg):
    if msg.get("list_unsubscribe"):
        return True
    labels = msg.get("labels", []) or []
    if "CATEGORY_PROMOTIONS" in labels or "CATEGORY_UPDATES" in labels:
        return True
    from_addr = _email_addr(msg.get("from", ""))
    return any(d in from_addr for d in NEWSLETTER_DOMAINS)


def _is_action(msg):
    if msg.get("is_calendar"):
        return True
    if msg.get("has_attachments"):
        return True
    haystack = f"{msg.get('subject', '')}\n{msg.get('snippet', '')}\n{msg.get('body', '')[:1000]}"
    return bool(ACTION_PATTERN.search(haystack))


def _is_needs_reply(msg):
    me = (msg.get("me_email") or "").lower()
    if not me:
        return False
    to_field = (msg.get("to") or "").lower()
    cc_field = (msg.get("cc") or "").lower()
    in_to = me in to_field
    in_cc_only = (not in_to) and (me in cc_field)
    if in_cc_only:
        return False
    body = msg.get("body") or msg.get("snippet") or ""
    if "?" in body[:2000]:
        return True
    last_line = body.strip().splitlines()[-1] if body.strip() else ""
    return last_line.endswith("?")


def categorize(messages):
    out = {key: [] for key in SECTIONS}
    for msg in messages:
        if _is_newsletter(msg):
            out["newsletters"].append(msg)
        elif _is_action(msg):
            out["action"].append(msg)
        elif _is_needs_reply(msg):
            out["needs_reply"].append(msg)
        else:
            out["fyi"].append(msg)
    return out
