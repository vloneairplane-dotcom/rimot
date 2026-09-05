import os
from datetime import datetime, timezone
from typing import Dict, Set
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import String, DateTime, JSON, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

app = FastAPI(title="Android Remote Manager", version="0.2.0")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://remote_manager:remote_manager@localhost:5432/remote_manager"
)
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

class Device(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    device_identifier: Mapped[str] = mapped_column(String(200), unique=True)
    android_version: Mapped[str] = mapped_column(String(50))
    app_version: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="offline")
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(100))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

devices: Dict[str, dict] = {}
dashboard_clients: Set[WebSocket] = set()
device_clients: Dict[str, WebSocket] = {}
ALLOWED_COMMANDS = {"get_device_info", "get_status", "sync_status"}

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    device_identifier: str = Field(min_length=3, max_length=200)
    android_version: str = Field(min_length=1, max_length=50)
    app_version: str = Field(min_length=1, max_length=50)

class CommandRequest(BaseModel):
    type: str
    payload: dict = {}

def now():
    return datetime.now(timezone.utc)

async def audit(device_id, action, metadata=None):
    async with Session() as s:
        s.add(AuditLog(
            id=str(uuid4()), device_id=device_id, action=action,
            metadata_json=metadata or {}, created_at=now()
        ))
        await s.commit()

async def broadcast(event):
    dead = []
    for ws in list(dashboard_clients):
        try: await ws.send_json(event)
        except Exception: dead.append(ws)
    for ws in dead: dashboard_clients.discard(ws)

async def dispatch_command(device_id, command_type, payload):
    if device_id not in devices: return "Device not found."
    if command_type not in ALLOWED_COMMANDS: return "Command is not allowlisted."
    ws = device_clients.get(device_id)
    if not ws: return "Device is offline."
    command_id = str(uuid4())
    await ws.send_json({
        "event":"command", "command_id":command_id,
        "type":command_type, "payload":payload
    })
    await audit(device_id, "command_sent", {"command_id": command_id, "type": command_type})
    return f"Command sent: {command_type}"

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Webhook mode keeps Telegram delivery compatible with Render, Railway, or a manual PUBLIC_URL.
    from .telegram_bot import build_bot
    bot = build_bot()
    if bot:
        app.state.telegram_bot = bot
        await bot.initialize()
        public_url = os.getenv("PUBLIC_URL", "").rstrip("/")
        if not public_url and os.getenv("RENDER_EXTERNAL_URL"):
            public_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
        if not public_url and os.getenv("RAILWAY_PUBLIC_DOMAIN"):
            public_url = f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN')}"
        webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
        if public_url:
            await bot.bot.set_webhook(
                url=f"{public_url}/telegram/webhook",
                secret_token=webhook_secret or None,
                allowed_updates=["message", "callback_query"],
            )

@app.on_event("shutdown")
async def shutdown():
    bot = getattr(app.state, "telegram_bot", None)
    if bot:
        await bot.updater.stop()
        await bot.stop()
        await bot.shutdown()
    await engine.dispose()

@app.get("/health")
async def health(): return {"ok": True, "time": now().isoformat()}

@app.post("/telegram/webhook")
async def telegram_webhook(request: "Request"):
    if not getattr(app.state, "telegram_bot", None):
        raise HTTPException(503, "telegram bot is not configured")
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    received = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret and received != secret:
        raise HTTPException(403, "invalid webhook secret")
    update = await request.json()
    from telegram import Update
    await app.state.telegram_bot.process_update(
        Update.de_json(update, app.state.telegram_bot.bot)
    )
    return {"ok": True}

@app.post("/devices/pair")
async def pair(req: RegisterRequest):
    async with Session() as s:
        existing = (await s.execute(
            select(Device).where(Device.device_identifier == req.device_identifier)
        )).scalar_one_or_none()
        if existing:
            device_id = existing.id
        else:
            device_id = str(uuid4())
            s.add(Device(id=device_id, **req.model_dump(), status="offline"))
            await s.commit()
    devices[device_id] = {
        "id": device_id, **req.model_dump(), "status": "offline",
        "last_seen": None, "created_at": now().isoformat()
    }
    await broadcast({"event":"device_registered", "device":devices[device_id]})
    return {"device_id":device_id, "device":devices[device_id]}

@app.get("/devices")
async def list_devices(): return list(devices.values())

@app.get("/devices/{device_id}")
async def get_device(device_id):
    if device_id not in devices: raise HTTPException(404, "device not found")
    return devices[device_id]

@app.post("/devices/{device_id}/commands")
async def command(device_id, req: CommandRequest):
    result = await dispatch_command(device_id, req.type, req.payload)
    if result.startswith("Device not found"): raise HTTPException(404, result)
    if result.startswith("Command is"): raise HTTPException(400, result)
    if result.startswith("Device is"): raise HTTPException(409, result)
    return {"ok": True, "message": result}

@app.websocket("/ws/device/{device_id}")
async def device_ws(websocket: WebSocket, device_id: str):
    await websocket.accept()
    if device_id not in devices:
        await websocket.close(code=1008); return
    device_clients[device_id] = websocket
    devices[device_id]["status"] = "online"
    devices[device_id]["last_seen"] = now().isoformat()
    await audit(device_id, "device_online")
    await broadcast({"event":"device_online", "device":devices[device_id]})
    try:
        while True:
            msg = await websocket.receive_json()
            devices[device_id]["last_seen"] = now().isoformat()
            if msg.get("event") == "status":
                devices[device_id].update(msg.get("data", {}))
                await broadcast({"event":"status_update","device":devices[device_id]})
            elif msg.get("event") == "command_result":
                await audit(device_id, "command_result", msg)
                await broadcast({"event":"command_result","device_id":device_id,"data":msg})
    except WebSocketDisconnect:
        pass
    finally:
        if device_clients.get(device_id) is websocket: del device_clients[device_id]
        devices[device_id]["status"] = "offline"
        await audit(device_id, "device_offline")
        await broadcast({"event":"device_offline","device":devices[device_id]})

@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await websocket.accept()
    dashboard_clients.add(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        dashboard_clients.discard(websocket)
