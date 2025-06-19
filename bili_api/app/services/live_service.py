import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from fastapi import HTTPException, WebSocket, WebSocketDisconnect

from ..core.config import settings
from .room_manager import room_manager
from ..schemas.room import (
    RoomDetail, LiveStatus, AnchorInfo, 
    RoomConnectionStatus, RoomInfoResponse,
    RoomConnectionResponse, RoomListResponse
)


logger = logging.getLogger(__name__)


class LiveService:
    """直播服务，提供API访问接口"""
    
    @staticmethod
    async def get_room_info(room_id: int) -> RoomInfoResponse:
        """获取房间信息"""
        # 尝试从已连接的房间获取信息
        room = room_manager.get_room(room_id)
        if room and room.room_info:
            return LiveService._create_room_info_response(room.room_info)
        
        # 如果房间未连接或没有缓存信息，连接并获取
        connected = await room_manager.connect_room(room_id)
        if not connected:
            raise HTTPException(status_code=500, detail=f"Failed to connect to room {room_id}")
        
        # 获取房间信息
        room_info = await room_manager.refresh_room_info(room_id)
        if not room_info:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not found or info not available")
        
        return LiveService._create_room_info_response(room_info)
    
    @staticmethod
    async def connect_room(room_id: int, cookies: Optional[str] = None, auto_reconnect: bool = True) -> RoomConnectionResponse:
        """连接到直播间"""
        # 连接房间
        connected = await room_manager.connect_room(room_id, cookies, auto_reconnect)
        if not connected:
            raise HTTPException(status_code=500, detail=f"Failed to connect to room {room_id}")
        
        # 获取房间状态
        status = room_manager.get_room_status(room_id)
        if not status:
            raise HTTPException(status_code=500, detail=f"Failed to get status for room {room_id}")
        
        return RoomConnectionResponse(
            code=0,
            message="success",
            data=RoomConnectionStatus(
                room_id=room_id,
                connected=status["connected"],
                connect_time=status["connect_time"],
                danmaku_count=status["danmaku_count"],
                gift_count=status["gift_count"]
            )
        )
    
    @staticmethod
    async def disconnect_room(room_id: int) -> Dict[str, Any]:
        """断开直播间连接"""
        # 断开房间连接
        disconnected = await room_manager.disconnect_room(room_id)
        if not disconnected:
            raise HTTPException(status_code=404, detail=f"Room {room_id} not connected")
        
        return {
            "code": 0,
            "message": "success",
            "data": {
                "room_id": room_id,
                "disconnected": True
            }
        }
    
    @staticmethod
    async def get_all_rooms() -> RoomListResponse:
        """获取所有已连接的房间"""
        # 获取所有房间状态
        statuses = room_manager.get_all_room_status()
        
        room_statuses = [
            RoomConnectionStatus(
                room_id=status["room_id"],
                connected=status["connected"],
                connect_time=status["connect_time"],
                danmaku_count=status["danmaku_count"],
                gift_count=status["gift_count"]
            )
            for status in statuses
        ]
        
        return RoomListResponse(
            code=0,
            message="success",
            data=room_statuses
        )
    
    @staticmethod
    async def handle_websocket(room_id: int, websocket: WebSocket):
        """处理WebSocket连接"""
        # 等待连接
        await websocket.accept()
        
        try:
            # 注册WebSocket
            registered = await room_manager.register_websocket(room_id, websocket)
            if not registered:
                await websocket.close(code=1001, reason=f"Failed to connect to room {room_id}")
                return
            
            # 发送连接成功消息
            await websocket.send_json({
                "event": "connected",
                "data": {
                    "room_id": room_id,
                    "timestamp": datetime.now().isoformat(),
                    "msg_type": "system",
                    "message": f"Connected to room {room_id}"
                }
            })
            
            # 保持连接直到客户端断开
            while True:
                # 接收客户端消息（可以用于心跳检测）
                data = await websocket.receive_text()
                logger.debug(f"Received from websocket: {data}")
        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected from room {room_id}")
        except Exception as e:
            logger.error(f"Error in websocket connection: {e}")
        finally:
            # 注销WebSocket
            await room_manager.unregister_websocket(room_id, websocket)
    
    @staticmethod
    def _create_room_info_response(room_info: Dict[str, Any]) -> RoomInfoResponse:
        """创建房间信息响应"""
        live_status_value = room_info.get("live_status", 0)
        
        # 处理live_time时间戳，可能是字符串或整数
        live_time = room_info.get("live_time")
        if live_time:
            try:
                if isinstance(live_time, str):
                    # 尝试解析ISO格式的时间字符串
                    if 'T' in live_time or '-' in live_time:
                        live_start_time = datetime.fromisoformat(live_time.replace('Z', '+00:00'))
                    else:
                        # 尝试将字符串转换为整数时间戳
                        live_start_time = datetime.fromtimestamp(int(live_time))
                else:
                    # 直接使用整数时间戳
                    live_start_time = datetime.fromtimestamp(live_time)
            except (ValueError, TypeError):
                logger.warning(f"无法解析live_time: {live_time}，使用当前时间")
                live_start_time = datetime.now()
        else:
            live_start_time = None
        
        room_detail = RoomDetail(
            room_id=room_info.get("room_id"),
            short_id=room_info.get("short_id", 0),
            title=room_info.get("title", ""),
            live_status=LiveStatus(
                live_status=live_status_value,
                live_start_time=live_start_time,
                online=room_info.get("online", 0)
            ),
            anchor_info=AnchorInfo(
                uid=room_info.get("uid"),
                uname=room_info.get("uname", "Unknown"),  # 使用API返回的主播名称
                face=room_info.get("face", None),
                gender=room_info.get("gender", None),
                level=room_info.get("level", None)
            ),
            area_id=room_info.get("area_id", 0),
            area_name=room_info.get("area_name", ""),
            parent_area_id=room_info.get("parent_area_id", 0),
            parent_area_name=room_info.get("parent_area_name", ""),
            cover=room_info.get("user_cover", None),
            tags=room_info.get("tags", ""),
            description=room_info.get("description", ""),
            attention=room_info.get("attention", 0)
        )
        
        return RoomInfoResponse(
            code=0,
            message="success",
            data=room_detail
        )


# 全局服务实例
live_service = LiveService() 