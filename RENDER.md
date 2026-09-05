# Render deployment

1. Push this repository to GitHub.
2. Open Render and create a Blueprint from the repository.
3. Render reads `render.yaml` and creates:
   - `android-remote-manager-api` (free Docker web service)
   - `android-remote-manager-dashboard` (free static site)
   - `android-remote-manager-db` (free PostgreSQL)
4. During setup, enter:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_ADMIN_IDS`
5. Deploy.
6. Open the API URL and verify `/health`.
7. Open the dashboard URL.
8. Message your Telegram bot with `/start`.

The bot uses a webhook at `/telegram/webhook`. The API URL is supplied by Render through `RENDER_EXTERNAL_URL`.

Important free-tier constraints:
- Render free web services can spin down after 15 minutes without inbound traffic.
- Free Postgres is limited to 1 GB and expires after 30 days.
- WebSocket connections can be interrupted when an instance is restarted or redeployed, so the Android client should reconnect automatically.
- Use `wss://` for public WebSocket connections.

For production, replace generated/default secrets, use a persistent paid database, add real device authentication, and put all public traffic behind HTTPS/WSS.
