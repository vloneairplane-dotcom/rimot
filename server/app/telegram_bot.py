import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes
)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = {int(x) for x in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",") if x.strip()}

# Runtime state is deliberately small; authoritative device data belongs in PostgreSQL.
API_BASE = os.getenv("PUBLIC_API_BASE", "http://api:8000")

def is_admin(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id in ADMIN_IDS)

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Devices", callback_data="devices")],
        [InlineKeyboardButton("📜 Activity", callback_data="activity")],
        [InlineKeyboardButton("➕ Pair device", callback_data="pair_help")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.effective_message.reply_text("Access denied.")
        return
    await update.effective_message.reply_text("Android Remote Manager", reply_markup=menu())

async def devices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    from .main import devices as runtime_devices
    if not runtime_devices:
        await update.effective_message.reply_text("No paired devices.")
        return
    rows = []
    for d in runtime_devices.values():
        icon = "🟢" if d["status"] == "online" else "🔴"
        rows.append([InlineKeyboardButton(
            f'{icon} {d["name"]}', callback_data=f'device:{d["id"]}'
        )])
    await update.effective_message.reply_text(
        "Devices:", reply_markup=InlineKeyboardMarkup(rows)
    )

async def device_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    device_id = q.data.split(":", 1)[1]
    from .main import devices as runtime_devices
    d = runtime_devices.get(device_id)
    if not d:
        await q.edit_message_text("Device not found.")
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Status", callback_data=f"cmd:{device_id}:get_status")],
        [InlineKeyboardButton("ℹ️ Device info", callback_data=f"cmd:{device_id}:get_device_info")],
        [InlineKeyboardButton("🔄 Sync status", callback_data=f"cmd:{device_id}:sync_status")],
        [InlineKeyboardButton("📜 Logs", callback_data=f"logs:{device_id}")],
    ])
    await q.edit_message_text(
        f'{d["name"]}\nStatus: {d["status"]}\nAndroid: {d["android_version"]}\n'
        f'App: {d["app_version"]}\nLast seen: {d["last_seen"] or "never"}',
        reply_markup=kb
    )

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    q = update.callback_query
    if q.data == "devices":
        await devices(update, context)
    elif q.data == "pair_help":
        await q.answer()
        await q.edit_message_text("Open the Android app and use its explicit pairing flow.")
    elif q.data.startswith("device:"):
        await device_menu(update, context)
    elif q.data.startswith("cmd:"):
        await q.answer()
        _, device_id, cmd = q.data.split(":", 2)
        from .main import dispatch_command
        result = await dispatch_command(device_id, cmd, {})
        await q.message.reply_text(result)
    elif q.data.startswith("logs:"):
        await q.answer("Audit logging is exposed through the API/dashboard.")

def build_bot():
    if not BOT_TOKEN:
        return None
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("devices", devices))
    app.add_handler(CallbackQueryHandler(callback))
    return app
