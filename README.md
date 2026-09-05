# Android Remote Manager — Telegram Edition

## Components
- Android Client
- FastAPI API + WebSocket gateway
- PostgreSQL persistence
- React dashboard
- Telegram Bot admin panel

## Telegram setup
1. Create a bot with BotFather.
2. Copy `.env.example` to `.env`.
3. Set `TELEGRAM_BOT_TOKEN`.
4. Set `TELEGRAM_ADMIN_IDS` to your Telegram numeric ID(s).
5. Run `docker compose up --build`.

The bot provides device listing, device selection, status/device-info commands, pairing guidance, and audit hooks.

## Android capabilities
The client must request Android permissions through the OS and use user-visible APIs such as Photo Picker / Storage Access Framework. The server does not bypass Android permissions.

## Production
Replace the development secrets, put API/WebSocket behind HTTPS/WSS, add real JWT/device credentials, migrations, object storage, and backups before deployment.
