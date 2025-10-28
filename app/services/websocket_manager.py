# app/services/websocket_manager.py

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Any

class ConnectionManager:
    def __init__(self):
        # Lưu trữ kết nối theo exam_id (hoặc id tác vụ)
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, exam_id: int):
        await websocket.accept()
        if exam_id not in self.active_connections:
            self.active_connections[exam_id] = []
        self.active_connections[exam_id].append(websocket)

    def disconnect(self, websocket: WebSocket, exam_id: int):
        self.active_connections.get(exam_id, []).remove(websocket)

    async def send_update_to_client(self, exam_id: int, message: Dict[str, Any]):
        """Gửi JSON message tới tất cả các client đang theo dõi exam_id này."""
        connections = self.active_connections.get(exam_id, [])
        for connection in connections:
            try:
                await connection.send_json(message)
            except RuntimeError:
                # Xử lý socket bị đóng đột ngột
                self.active_connections.get(exam_id, []).remove(connection)
                pass 

manager = ConnectionManager()