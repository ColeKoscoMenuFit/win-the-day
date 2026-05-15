"""Claude-powered draft reply generator."""

import os
import threading

import anthropic

_CLIENT = None
_CACHE = {}
_LOCK = threading.Lock()

MODEL = "claude-opus-4-7"

SYSTEM_PROMPT = """You are drafting reply emails on behalf of the user.

Voice and rules:
- Write in a concise, warm, professional tone — the way a thoughtful person on email replies.
- Match the register of the incoming message (casual gets casual, formal gets formal).
- Address the sender's actual points; if they asked a question, answer it directly.
- Keep replies short by default (2-5 sentences) unless the thread clearly warrants more.
- Do not invent facts, commitments, dates, or numbers. If something is unknown, say so or ask.
- No subject line, no greeting block formatting beyond a natural opener.
- Sign off with a single line like "Thanks," — do NOT add a name; the user signs it.
- Output ONLY the body text of the reply. No preamble, no explanation, no markdown."""


def _client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic()
    return _CLIENT


def _format_thread(thread_messages, me_email):
    parts = []
    for m in thread_messages[-3:]:
        sender = m.get("from", "unknown")
        date = m.get("date", "")
        body = (m.get("body") or "").strip()
        if len(body) > 4000:
            body = body[:4000] + "\n[...truncated]"
        parts.append(f"From: {sender}\nDate: {date}\n\n{body}")
    sep = "\n\n---\n\n"
    return f"My email address: {me_email}\n\nThread (oldest → newest):\n\n{sep.join(parts)}"


def generate_draft(thread_id, thread_messages, me_email, force=False):
    with _LOCK:
        if not force and thread_id in _CACHE:
            return _CACHE[thread_id]

    user_content = _format_thread(thread_messages, me_email)
    user_content += "\n\nDraft a reply now. Output only the reply body."

    if not os.environ.get("ANTHROPIC_API_KEY"):
        last = thread_messages[-1] if thread_messages else {}
        sender = (last.get("from") or "").split("<")[0].split("@")[0].strip() or "there"
        draft = (
            f"Thanks for your note, {sender.split()[0] if sender else 'there'}. "
            f"Let me circle back with a proper response shortly.\n\n"
            f"Thanks,\n\n"
            f"[Demo draft — set ANTHROPIC_API_KEY to enable real AI drafts.]"
        )
    else:
        response = _client().messages.create(
            model=MODEL,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
        )
        draft = "".join(b.text for b in response.content if b.type == "text").strip()

    with _LOCK:
        _CACHE[thread_id] = draft
    return draft


def clear_cache():
    with _LOCK:
        _CACHE.clear()
