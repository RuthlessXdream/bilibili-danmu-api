from fastapi import APIRouter, Path, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from typing import Dict, List, Any, Optional

from ..services.live_service import live_service
from ..schemas.room import (
    RoomInfoRequest, RoomConnectRequest, RoomDisconnectRequest,
    RoomInfoResponse, RoomConnectionResponse, RoomListResponse
)


router = APIRouter()


@router.get("/rooms/{room_id}", response_model=RoomInfoResponse, summary="获取房间信息")
async def get_room_info(
    room_id: int = Path(..., description="房间ID", gt=0)
):
    """
    获取指定房间的详细信息，包括直播状态、主播信息等。
    
    - **room_id**: 房间ID
    
    返回房间的详细信息。
    """
    return await live_service.get_room_info(room_id)


@router.post("/rooms/{room_id}/connect", response_model=RoomConnectionResponse, summary="连接房间")
async def connect_room(
    room_id: int = Path(..., description="房间ID", gt=0),
    request: RoomConnectRequest = None
):
    """
    连接到指定的房间，开始接收直播数据。
    
    - **room_id**: 房间ID
    - **cookies**: (可选) B站cookies，用于获取更多权限
    - **auto_reconnect**: (可选) 断开后是否自动重连，默认为True
    
    返回连接状态信息。
    """
    if request is None:
        request = RoomConnectRequest(room_id=room_id)
    elif request.room_id != room_id:
        raise HTTPException(status_code=400, detail="Room ID in path and body must match")
    
    return await live_service.connect_room(
        room_id=room_id,
        cookies=request.cookies,
        auto_reconnect=request.auto_reconnect
    )


@router.post("/rooms/{room_id}/disconnect", summary="断开房间连接")
async def disconnect_room(
    room_id: int = Path(..., description="房间ID", gt=0)
):
    """
    断开与指定房间的连接，停止接收直播数据。
    
    - **room_id**: 房间ID
    
    返回断开连接状态。
    """
    return await live_service.disconnect_room(room_id)


@router.get("/rooms", response_model=RoomListResponse, summary="获取所有已连接房间")
async def get_all_rooms():
    """
    获取所有已连接的房间列表及其状态。
    
    返回房间状态列表。
    """
    return await live_service.get_all_rooms() 