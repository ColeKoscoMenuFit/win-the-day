# Win The Day

A small toolbox for staying focused.

- **`wtd.py`** — terminal Signal-vs-Noise planner (Textual TUI).
- **`app.py`** — Gmail dashboard: unread/needs-reply mail sorted into 4 buckets, with AI-drafted replies you can edit and send through your real Gmail.

---

## Win The Day Mail (Gmail dashboard)

A local web app that pulls your unread Gmail, sorts it into **Needs Reply / Action / FYI / Newsletters**, generates a draft reply for each email using Claude, and lets you edit and send through your Gmail account.

### Setup

#### 1. Get Gmail API credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or pick an existing one).
3. **APIs & Services → Library** → enable **Gmail API**.
4. **APIs & Services → OAuth consent screen** → set up the consent screen as an **External** app. Add yourself as a test user.
5. **APIs & Services → Credentials** → **Create Credentials → OAuth client ID** → choose **Desktop app** → download the JSON.
6. Save the downloaded file as `credentials.json` in this repo's root.

#### 2. Get an Anthropic API key

1. Go to [console.anthropic.com](https://console.anthropic.com/) → API Keys.
2. Create a key.
3. Copy `.env.example` to `.env` and paste your key in:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

(Use a virtualenv if you prefer: `python -m venv venv && source venv/bin/activate` first.)

#### 4. Run it

```bash
python app.py
```

The first run opens a browser to authorize Gmail access — sign in and grant the requested scopes. After that, the token is cached in `token.json` and you won't be re-prompted.

Open **http://localhost:5000** in your browser.

### Preview without setup (demo mode)

Want to see the UI before wiring up Gmail? Run:

```bash
WTD_DEMO=1 python app.py
```

This loads a fake inbox of 10 emails so you can poke at the dashboard. Set your `ANTHROPIC_API_KEY` to also see real Claude drafts; without it you'll get placeholder drafts. Demo mode also activates automatically if `credentials.json` is missing.

### What you can do

- See all your unread inbox mail bucketed into 4 columns.
- Click any email to expand: full message + a Claude-generated draft reply.
- Edit the draft in place. Hit **Send** — it goes through your real Gmail, threaded with the original.
- **Regenerate** asks Claude for a different draft.
- **Refresh** re-pulls Gmail and re-buckets.

### Files

| File | Purpose |
| --- | --- |
| `app.py` | Flask server + JSON API |
| `gmail_client.py` | Gmail OAuth, list/get/send |
| `categorizer.py` | Rule-based 4-bucket sort |
| `ai_drafter.py` | Claude draft generation (with prompt caching) |
| `templates/dashboard.html` | UI shell |
| `static/style.css`, `static/app.js` | Frontend |
| `credentials.json` | Your Google OAuth client (gitignored) |
| `token.json` | Cached Gmail token (gitignored, auto-created) |
| `.env` | Your Anthropic API key (gitignored) |

### Notes

- Scope used: `gmail.modify` — read, send, mark as read. No delete.
- All data stays local. Drafts run through Anthropic's API; nothing is stored anywhere but your machine.
- Categorization is rule-based (no LLM) for speed. Tune the rules in `categorizer.py`.

---

## Win The Day (original TUI)

```bash
python wtd.py
```

Track today's signals vs noise. See `wtd.py` for the keybindings.
