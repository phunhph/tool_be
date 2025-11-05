from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import manager

ws_router = APIRouter()

@ws_router.websocket("/ws/{exam_id}")
async def websocket_endpoint(websocket: WebSocket, exam_id: int):
    await manager.connect(websocket, exam_id)
    try:
        while True:
            # giữ kết nối sống, client có thể gửi ping/pong
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, exam_id)
