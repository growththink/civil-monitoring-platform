"""WebSocket realtime endpoint. Auth via ?token=<JWT>."""
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.logging import get_logger
from app.core.security import decode_token
from app.ws.manager import broadcaster

router = APIRouter()
log = get_logger(__name__)


@router.websocket("/ws")
async def ws_global(websocket: WebSocket, token: str = Query(...)):
    """Global stream: receives all readings + alerts."""
    try:
        decode_token(token)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    await broadcaster.subscribe_global(websocket)
    try:
        while True:
            await websocket.receive_text()  # ping/pong; client may send {"type":"ping"}
    except WebSocketDisconnect:
        pass
    finally:
        await broadcaster.disconnect(websocket)


@router.websocket("/ws/sites/{site_id}")
async def ws_site(
    websocket: WebSocket,
    site_id: uuid.UUID,
    token: str = Query(...),
):
    """Per-site stream."""
    try:
        decode_token(token)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    await broadcaster.subscribe_site(str(site_id), websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await broadcaster.disconnect(websocket)
