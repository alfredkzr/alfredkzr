import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.event_bus import event_bus

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    queue = event_bus.subscribe()

    try:
        while True:
            event = await queue.get()
            await websocket.send_text(json.dumps(event, default=str))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        event_bus.unsubscribe(queue)
