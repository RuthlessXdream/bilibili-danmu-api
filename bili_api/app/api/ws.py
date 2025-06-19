from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Path, Query, HTTPException
from typing import Dict, Any

from ..services.live_service import live_service


router = APIRouter()


@router.websocket("/ws/rooms/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int = Path(..., description="房间ID", gt=0)
):
    """
    WebSocket连接，用于实时接收指定房间的直播数据。
    
    - **room_id**: 房间ID
    
    通过WebSocket连接接收直播数据，包括弹幕、礼物、上舰等实时消息。
    
    消息格式：
    ```json
    {
        "event": "事件类型",
        "data": {
            "room_id": 房间ID,
            "timestamp": "时间戳",
            "msg_type": "消息类型",
            ...其他数据
        }
    }
    ```
    
    事件类型包括：
    - heartbeat: 心跳消息
    - danmaku: 弹幕消息
    - gift: 礼物消息
    - guard_buy: 上舰消息
    - super_chat: 醒目留言消息
    - room_change: 房间信息变更消息
    - live_status_change: 直播状态变更消息
    """
    await live_service.handle_websocket(room_id, websocket) 