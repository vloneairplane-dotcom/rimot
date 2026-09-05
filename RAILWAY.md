# Railway deployment

This repo now deploys as three separate Railway services inside one project:

1. **Postgres** — Railway's managed database plugin.
2. **api** — the FastAPI backend (`server/`).
3. **dashboard** — the React dashboard (`dashboard/`).

## 1. Push to GitHub
Railway deploys from a GitHub repo. Push this project to a repo first.

## 2. Create the project
1. Go to https://railway.com/new and choose **Deploy from GitHub repo**.
2. Select your repo. Railway will create one service from the repo root — delete it
   or repurpose it as the `api` service in the next step (set its Root Directory).

## 3. Add the Postgres database
1. In the project, click **+ New → Database → Add PostgreSQL**.
2. Railway creates a `Postgres` service with a `DATABASE_URL` variable automatically.

## 4. Configure the `api` service
1. On the service, open **Settings**:
   - **Root Directory**: `server`
   - Railway auto-detects `server/Dockerfile` (and reads `server/railway.json`).
2. Open **Variables** and add:
   - `DATABASE_URL` → click the "reference" icon and pick `Postgres.DATABASE_URL`
     (the app expects the `postgresql+asyncpg://` driver — see note below).
   - `TELEGRAM_BOT_TOKEN` → your BotFather token.
   - `TELEGRAM_ADMIN_IDS` → your numeric Telegram user ID(s), comma-separated.
   - `TELEGRAM_WEBHOOK_SECRET` → any random string.
3. Click **Settings → Networking → Generate Domain** to get a public
   `*.up.railway.app` URL. The app reads `RAILWAY_PUBLIC_DOMAIN` automatically
   (Railway sets this for you) to register the Telegram webhook — no extra
   variable needed. If you attach a custom domain instead, set `PUBLIC_URL`
   to `https://your-domain` explicitly.

   **Postgres driver note:** Railway's `DATABASE_URL` reference is a plain
   `postgresql://...` URL, but this app's SQLAlchemy engine expects the async
   driver prefix `postgresql+asyncpg://...`. Easiest fix: add a second variable
   `DATABASE_URL` with value:
   `${{Postgres.DATABASE_URL}}` and then in the same field replace the scheme,
   e.g. set it manually to
   `postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}`
   using Railway's variable reference syntax.

## 5. Configure the `dashboard` service
1. Click **+ New → GitHub Repo** again, select the same repo, and set:
   - **Root Directory**: `dashboard`
2. Open **Variables** and add:
   - `VITE_API_BASE` → the api service's public URL from step 4
     (e.g. `https://api-production-xxxx.up.railway.app`). This is baked in
     at build time, so set it before the first deploy (or redeploy after
     adding it).
3. Generate a public domain for this service too (**Settings → Networking**).

## 6. Deploy and verify
1. Both services redeploy automatically on push/variable changes.
2. Open the `api` domain + `/health` — should return `{"ok": true, ...}`.
3. Open the `dashboard` domain — should load the device list UI.
4. Message your Telegram bot with `/start` — you should see the admin menu.

## 7. Building the Android APK
`android-client/` is Kotlin source, not a compiled app. A GitHub Actions
workflow (`.github/workflows/android-build.yml`) builds a debug APK
automatically on every push to `main` that touches `android-client/`.

1. Push this repo to GitHub (if not already).
2. Open the repo's **Actions** tab, wait for "Build Android APK" to finish.
3. Download the `android-remote-manager-debug-apk` artifact from the run —
   it contains `app-debug.apk`, installable on any Android 8.0+ (API 26+) device.

The client's server address (`MainActivity.kt`) already points at
`wss://android-remote-manager-api-production-a8e5.up.railway.app` — update
this if you regenerate the api service's domain.

Note: the current `MainActivity` has no UI yet (no pairing screen, no button
to trigger `connect()`) — it's a starter you'll need to build a real screen
on top of before it's usable end-to-end.

## Notes
- Railway services restart on crash based on `railway.json`
  (`restartPolicyType: ON_FAILURE`).
- WebSocket connections can drop on redeploy — the Android client should
  reconnect automatically (add retry logic if not already present).
- For production: rotate all secrets, add real device authentication
  (the current pairing flow has no auth), and put the API behind your own
  auth/JWT layer before exposing it publicly.
