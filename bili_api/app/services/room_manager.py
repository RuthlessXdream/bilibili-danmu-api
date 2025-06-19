import sys
import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Set, Optional, List, Any, Callable
from datetime import datetime

import aiohttp
from fastapi import WebSocket

from ..core.config import settings

# 动态导入blivedm模块
def import_blivedm():
    blivedm_path = settings.BLIVEDM_PATH
    if not blivedm_path.exists():
        raise ImportError(f"blivedm path not found: {blivedm_path}")
    
    # 确保父目录在sys.path中
    parent_dir = str(blivedm_path.parent)
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    
    # 动态导入blivedm模块
    sys.path.append(str(blivedm_path))
    import blivedm
    return blivedm

# 导入blivedm模块
blivedm = import_blivedm()

logger = logging.getLogger(__name__)

# 请求头
HEADERS = {
    'User-Agent': settings.BILIBILI_USER_AGENT,
    'Referer': settings.BILIBILI_REFERER,
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
}

class RoomConnection:
    """直播间连接管理类"""
    
    def __init__(self, room_id: int, cookies: Optional[str] = None, auto_reconnect: bool = True):
        self.room_id = room_id
        self.cookies = cookies
        self.auto_reconnect = auto_reconnect
        self.client = None
        self.connected = False
        self.connect_time = None
        self.last_heartbeat = None
        self.client_session = None
        self.websocket_clients: Set[WebSocket] = set()
        self.danmaku_count = 0
        self.gift_count = 0
        self.room_info = {}
        
        # 消息处理器
        self.message_handlers = {}
        
    async def connect(self):
        """连接到直播间"""
        if self.connected:
            return True
        
        try:
            # 创建会话，使用完整的HTTP头部
            self.client_session = aiohttp.ClientSession(headers=HEADERS)
            
            # 设置cookies
            if self.cookies:
                self.client_session.cookie_jar.update_cookies(self._parse_cookies(self.cookies))
            
            # 创建客户端
            self.client = blivedm.BLiveClient(self.room_id, session=self.client_session)
            handler = self._create_handler()
            self.client.set_handler(handler)
            
            # 启动客户端
            self.client.start()  # 不使用await，避免阻塞
            self.connected = True
            self.connect_time = datetime.now()
            logger.info(f"Connected to room {self.room_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to room {self.room_id}: {e}")
            await self.disconnect()
            return False
    
    async def disconnect(self):
        """断开直播间连接"""
        if not self.connected:
            return True
        
        try:
            if self.client:
                self.client.stop()
                await asyncio.sleep(1)  # 等待一会以确保资源释放
            
            if self.client_session:
                await self.client_session.close()
            
            self.connected = False
            self.client = None
            self.client_session = None
            logger.info(f"Disconnected from room {self.room_id}")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from room {self.room_id}: {e}")
            return False
    
    async def refresh_room_info(self):
        """刷新房间信息"""
        if not self.client_session:
            return None
        
        try:
            # 获取房间基本信息
            url = f"https://api.live.bilibili.com/room/v1/Room/get_info"
            params = {"room_id": self.room_id}
            async with self.client_session.get(url, params=params, headers=HEADERS) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("code") == 0:
                        self.room_info = data.get("data", {})
                        return self.room_info
            return None
        except Exception as e:
            logger.error(f"Failed to refresh room info for {self.room_id}: {e}")
            return None
    
    def register_websocket(self, websocket: WebSocket):
        """注册WebSocket连接"""
        self.websocket_clients.add(websocket)
        logger.info(f"WebSocket client registered for room {self.room_id}, total clients: {len(self.websocket_clients)}")
    
    def unregister_websocket(self, websocket: WebSocket):
        """注销WebSocket连接"""
        if websocket in self.websocket_clients:
            self.websocket_clients.remove(websocket)
            logger.info(f"WebSocket client unregistered for room {self.room_id}, total clients: {len(self.websocket_clients)}")
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """广播消息到所有WebSocket客户端"""
        disconnected_clients = set()
        
        for websocket in self.websocket_clients:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to WebSocket client: {e}")
                disconnected_clients.add(websocket)
        
        # 移除断开的连接
        for client in disconnected_clients:
            self.unregister_websocket(client)
    
    def get_status(self):
        """获取连接状态"""
        return {
            "room_id": self.room_id,
            "connected": self.connected,
            "connect_time": self.connect_time,
            "danmaku_count": self.danmaku_count,
            "gift_count": self.gift_count,
            "websocket_clients": len(self.websocket_clients),
            "last_heartbeat": self.last_heartbeat,
        }
    
    def _parse_cookies(self, cookies_string):
        """解析cookies字符串"""
        import http.cookies
        cookies = http.cookies.SimpleCookie()
        for cookie in cookies_string.split('; '):
            if '=' in cookie:
                key, value = cookie.split('=', 1)
                cookies[key] = value
                cookies[key]['domain'] = 'bilibili.com'
        return cookies
    
    def _create_handler(self):
        """创建blivedm消息处理器"""
        manager = self
        
        class MessageHandler(blivedm.BaseHandler):
            def _on_heartbeat(self, client, message):
                manager.last_heartbeat = datetime.now()
                manager._handle_message("heartbeat", message)
            
            def _on_danmaku(self, client, message):
                manager.danmaku_count += 1
                manager._handle_message("danmaku", message)
            
            def _on_gift(self, client, message):
                manager.gift_count += 1
                manager._handle_message("gift", message)
            
            def _on_buy_guard(self, client, message):
                manager._handle_message("guard_buy", message)
            
            def _on_super_chat(self, client, message):
                manager._handle_message("super_chat", message)
            
            def _on_super_chat_delete(self, client, message):
                manager._handle_message("super_chat_delete", message)
            
            def _on_interact_word(self, client, message):
                manager._handle_message("interact_word", message)
                
            def _on_room_change(self, client, message):
                manager._handle_message("room_change", message)
                
            def _on_live_status_change(self, client, message):
                manager._handle_message("live_status_change", message)
            
            def _on_error(self, client, exception):
                logger.error(f"Error in room {manager.room_id}: {exception}")
        
        return MessageHandler()
    
    def _handle_message(self, event_type, message):
        """处理并广播消息"""
        # 转换为通用消息格式
        timestamp = datetime.now().isoformat()
        
        data = {
            "event": event_type,
            "data": {
                "room_id": self.room_id,
                "timestamp": timestamp,
                "msg_type": event_type,
                **self._convert_message(event_type, message)
            }
        }
        
        # 广播消息
        asyncio.create_task(self.broadcast_message(data))
    
    def _convert_message(self, event_type, message):
        """转换blivedm消息为API消息格式"""
        if event_type == "heartbeat":
            return {
                "popularity": message.popularity
            }
        elif event_type == "danmaku":
            return {
                "uid": message.uid,
                "uname": message.uname,
                "content": message.msg,
                "face": message.face,
                "user_level": message.user_level,
                "medal_level": message.medal_level,
                "medal_name": message.medal_name,
                "medal_room_id": message.medal_room_id,
                "guard_level": message.privilege_type
            }
        elif event_type == "gift":
            return {
                "uid": message.uid,
                "uname": message.uname,
                "face": message.face,
                "gift_id": message.gift_id,
                "gift_name": message.gift_name,
                "gift_count": message.num,
                "price": message.price,
                "coin_type": message.coin_type,
                "total_coin": message.total_coin,
                "medal_level": message.medal_level,
                "medal_name": message.medal_name,
                "medal_room_id": message.medal_room_id,
                "guard_level": message.guard_level
            }
        elif event_type == "guard_buy":
            return {
                "uid": message.uid,
                "uname": message.username,
                "guard_level": message.guard_level,
                "gift_name": message.gift_name,
                "price": message.price,
                "num": message.num
            }
        elif event_type == "super_chat":
            return {
                "uid": message.uid,
                "uname": message.uname,
                "face": message.face,
                "price": message.price,
                "message": message.message,
                "message_trans": message.message_trans,
                "start_time": message.start_time,
                "end_time": message.end_time,
                "medal_level": message.medal_level,
                "medal_name": message.medal_name,
                "medal_room_id": message.medal_room_id,
                "guard_level": message.guard_level
            }
        elif event_type == "super_chat_delete":
            return {
                "ids": message.ids
            }
        elif event_type == "room_change":
            return {
                "title": getattr(message, "title", None),
                "area_id": getattr(message, "area_id", None),
                "area_name": getattr(message, "area_name", None),
                "parent_area_id": getattr(message, "parent_area_id", None),
                "parent_area_name": getattr(message, "parent_area_name", None)
            }
        elif event_type == "live_status_change":
            return {
                "live_status": getattr(message, "live_status", 0),
                "live_start_time": getattr(message, "live_time", None)
            }
        else:
            return {"raw_data": str(message)}


class RoomManager:
    """房间管理器，管理所有直播间连接"""
    
    def __init__(self):
        self.rooms: Dict[int, RoomConnection] = {}
        self.lock = asyncio.Lock()
    
    async def connect_room(self, room_id: int, cookies: Optional[str] = None, auto_reconnect: bool = True) -> bool:
        """连接到直播间"""
        async with self.lock:
            # 如果已连接，返回True
            if room_id in self.rooms and self.rooms[room_id].connected:
                return True
            
            # 创建或重用连接
            if room_id not in self.rooms:
                self.rooms[room_id] = RoomConnection(room_id, cookies, auto_reconnect)
            
            # 连接
            return await self.rooms[room_id].connect()
    
    async def disconnect_room(self, room_id: int) -> bool:
        """断开直播间连接"""
        async with self.lock:
            if room_id in self.rooms:
                result = await self.rooms[room_id].disconnect()
                del self.rooms[room_id]
                return result
            return False
    
    def get_room(self, room_id: int) -> Optional[RoomConnection]:
        """获取直播间连接"""
        return self.rooms.get(room_id)
    
    def get_all_rooms(self) -> List[RoomConnection]:
        """获取所有直播间连接"""
        return list(self.rooms.values())
    
    def get_room_status(self, room_id: int) -> Optional[Dict[str, Any]]:
        """获取直播间状态"""
        room = self.get_room(room_id)
        if room:
            return room.get_status()
        return None
    
    def get_all_room_status(self) -> List[Dict[str, Any]]:
        """获取所有直播间状态"""
        return [room.get_status() for room in self.rooms.values()]
    
    async def register_websocket(self, room_id: int, websocket: WebSocket) -> bool:
        """注册WebSocket连接"""
        room = self.get_room(room_id)
        if not room:
            connected = await self.connect_room(room_id)
            if not connected:
                return False
            room = self.get_room(room_id)
        
        room.register_websocket(websocket)
        return True
    
    async def unregister_websocket(self, room_id: int, websocket: WebSocket):
        """注销WebSocket连接"""
        room = self.get_room(room_id)
        if room:
            room.unregister_websocket(websocket)
    
    async def refresh_room_info(self, room_id: int) -> Optional[Dict[str, Any]]:
        """刷新直播间信息"""
        room = self.get_room(room_id)
        if room:
            return await room.refresh_room_info()
        return None


# 全局房间管理器实例
room_manager = RoomManager() 