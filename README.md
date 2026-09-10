# SwasthyaAI

A multilingual health-awareness chatbot. Ask health questions in any of 12
Indian languages and get clear, non-diagnostic guidance powered by Google
Gemini. Includes email/password and Google sign-in, with saved chat history for
signed-in users.

## ⚠️ Rotate your keys first

The `.env` you had contained a live-looking Google OAuth client secret and
Gemini API key. If that file was ever shared, committed, or pasted anywhere
outside your own machine, **rotate both immediately**:

- Gemini key: [Google AI Studio → API keys](https://aistudio.google.com/apikey) → delete the old one, create a new one.
- Google OAuth secret: [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials) → reset the client secret.

This project ships with `.env.example` (placeholders only) instead of a real
`.env`, on purpose — fill in your **new**, rotated values there.

## What was actually broken

- **Templates weren't in a `templates/` folder.** `app.py` calls
  `render_template("index.html")` / `render_template("dashboard.html")`,
  but Flask only looks inside `templates/` by default. The HTML files were
  sitting at the project root, so every page load would have thrown
  `TemplateNotFound` and the app couldn't run at all. Fixed by moving both
  files into `templates/`.
- **Local Google OAuth had no way to work over HTTP.** `app.py` respects
  `OAUTHLIB_INSECURE_TRANSPORT` from the environment, but it was never set
  anywhere, so Google sign-in on `http://localhost:5000` would fail with an
  `InsecureTransportError`. Added `OAUTHLIB_INSECURE_TRANSPORT=1` to
  `.env.example` (dev only — never set this in production, which must run
  over HTTPS).
- **Live secrets were sitting in a committed-looking `.env`.** See above.
- Minor polish: added a favicon to both pages so the tab doesn't look
  unfinished, and cleaned up stray files (`.gitignore`/`.env` had gotten
  saved as `_gitignore`/`_env` by whatever exported them).

The Flask backend, auth, and Gemini integration logic itself was solid —
no changes needed there beyond the fixes above.

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
cp .env.example .env            # then fill in real (rotated) values in .env

# 4. Run
python app.py
```

Open http://localhost:5000

## Environment variables

See `.env.example`. You need at minimum a `SECRET_KEY` and a `GEMINI_API_KEY`.
Google sign-in also needs `GOOGLE_OAUTH_CLIENT_ID` and
`GOOGLE_OAUTH_CLIENT_SECRET`, plus an authorized redirect URI in Google Cloud
Console of `http://localhost:5000/login/google/authorized` for local dev.
For local OAuth over http, `OAUTHLIB_INSECURE_TRANSPORT=1` is already set in
`.env.example` (never in production).

## Project structure

```
app.py                    Flask app: pages, auth, chat API, history API
chatbot.py                Gemini wrapper (prompt + call)
models.py                 SQLAlchemy models (User, Message)
templates/index.html      Landing page + guest chat + auth modal
templates/dashboard.html  Signed-in chat with saved history
static/                   Reserved for any future static assets
requirements.txt          Python dependencies
.env.example              Config template (copy to .env)
```

## Notes

- Guests can chat without an account; those messages are **not** saved.
- Signed-in users get saved history, and recent turns are fed back to the model
  for context.
- This app is for health **awareness** only. It does not diagnose and is not a
  substitute for professional medical care.

## Security

Never commit your real `.env`. If an API key or OAuth secret has ever been
shared or committed, rotate it immediately.
