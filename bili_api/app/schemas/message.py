from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class BaseMessage(BaseModel):
    """基础消息模型"""
    room_id: int = Field(..., description="房间ID")
    timestamp: datetime = Field(..., description="消息时间戳")
    msg_type: str = Field(..., description="消息类型")


class HeartbeatMessage(BaseMessage):
    """心跳消息"""
    msg_type: Literal["heartbeat"] = "heartbeat"
    popularity: int = Field(..., description="人气值")


class DanmakuMessage(BaseMessage):
    """弹幕消息"""
    msg_type: Literal["danmaku"] = "danmaku"
    uid: int = Field(..., description="用户ID")
    uname: str = Field(..., description="用户名")
    content: str = Field(..., description="弹幕内容")
    face: Optional[str] = Field(None, description="用户头像URL")
    user_level: int = Field(0, description="用户等级")
    medal_level: Optional[int] = Field(None, description="勋章等级")
    medal_name: Optional[str] = Field(None, description="勋章名称")
    medal_room_id: Optional[int] = Field(None, description="勋章房间ID")
    guard_level: int = Field(0, description="舰队等级: 0-非舰队, 1-总督, 2-提督, 3-舰长")


class GiftMessage(BaseMessage):
    """礼物消息"""
    msg_type: Literal["gift"] = "gift"
    uid: int = Field(..., description="用户ID")
    uname: str = Field(..., description="用户名")
    face: Optional[str] = Field(None, description="用户头像URL")
    gift_id: int = Field(..., description="礼物ID")
    gift_name: str = Field(..., description="礼物名称")
    gift_count: int = Field(..., description="礼物数量")
    price: int = Field(..., description="礼物单价(瓜子)")
    coin_type: str = Field(..., description="币种类型: 'silver'-银瓜子, 'gold'-金瓜子")
    total_coin: int = Field(..., description="总价值(瓜子)")
    medal_level: Optional[int] = Field(None, description="勋章等级")
    medal_name: Optional[str] = Field(None, description="勋章名称")
    medal_room_id: Optional[int] = Field(None, description="勋章房间ID")
    guard_level: int = Field(0, description="舰队等级: 0-非舰队, 1-总督, 2-提督, 3-舰长")


class SuperChatMessage(BaseMessage):
    """醒目留言消息"""
    msg_type: Literal["super_chat"] = "super_chat"
    uid: int = Field(..., description="用户ID")
    uname: str = Field(..., description="用户名")
    face: Optional[str] = Field(None, description="用户头像URL")
    price: int = Field(..., description="价格(人民币)")
    message: str = Field(..., description="留言内容")
    message_trans: Optional[str] = Field(None, description="翻译内容")
    start_time: int = Field(..., description="开始时间戳")
    end_time: int = Field(..., description="结束时间戳")
    medal_level: Optional[int] = Field(None, description="勋章等级")
    medal_name: Optional[str] = Field(None, description="勋章名称")
    medal_room_id: Optional[int] = Field(None, description="勋章房间ID")
    guard_level: int = Field(0, description="舰队等级: 0-非舰队, 1-总督, 2-提督, 3-舰长")


class GuardBuyMessage(BaseMessage):
    """上舰消息"""
    msg_type: Literal["guard_buy"] = "guard_buy"
    uid: int = Field(..., description="用户ID")
    uname: str = Field(..., description="用户名")
    guard_level: int = Field(..., description="舰队等级: 0-非舰队, 1-总督, 2-提督, 3-舰长")
    gift_name: str = Field(..., description="礼物名称")
    price: int = Field(..., description="单价(金瓜子)")
    num: int = Field(..., description="数量")


class RoomChangeMessage(BaseMessage):
    """房间状态变更消息"""
    msg_type: Literal["room_change"] = "room_change"
    title: Optional[str] = Field(None, description="标题")
    area_id: Optional[int] = Field(None, description="分区ID")
    area_name: Optional[str] = Field(None, description="分区名称")
    parent_area_id: Optional[int] = Field(None, description="父分区ID")
    parent_area_name: Optional[str] = Field(None, description="父分区名称")


class LiveStatusChangeMessage(BaseMessage):
    """直播状态变更消息"""
    msg_type: Literal["live_status_change"] = "live_status_change"
    live_status: int = Field(..., description="直播状态: 0-未开播, 1-直播中, 2-轮播中")
    live_start_time: Optional[datetime] = Field(None, description="开播时间")


class WebSocketMessage(BaseModel):
    """WebSocket消息包装"""
    event: str = Field(..., description="事件类型")
    data: Union[
        HeartbeatMessage, 
        DanmakuMessage, 
        GiftMessage, 
        SuperChatMessage, 
        GuardBuyMessage,
        RoomChangeMessage,
        LiveStatusChangeMessage,
        Dict[str, Any]
    ] = Field(..., description="消息数据")


class ErrorMessage(BaseModel):
    """错误消息"""
    code: int = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    data: Optional[Dict[str, Any]] = Field(None, description="附加数据") 