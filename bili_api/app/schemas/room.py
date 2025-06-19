from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime


class RoomInfoBase(BaseModel):
    """房间基本信息模型"""
    room_id: int = Field(..., description="房间ID")
    

class RoomInfoRequest(RoomInfoBase):
    """获取房间信息请求"""
    pass


class RoomConnectRequest(RoomInfoBase):
    """连接房间请求"""
    cookies: Optional[str] = Field(None, description="B站cookies，用于获取更多权限")
    auto_reconnect: bool = Field(True, description="断开后是否自动重连")


class RoomDisconnectRequest(RoomInfoBase):
    """断开房间连接请求"""
    pass


class LiveStatus(BaseModel):
    """直播状态"""
    live_status: int = Field(..., description="直播状态: 0-未开播, 1-直播中, 2-轮播中")
    live_start_time: Optional[datetime] = Field(None, description="开播时间")
    online: int = Field(0, description="在线人数")
    

class AnchorInfo(BaseModel):
    """主播信息"""
    uid: int = Field(..., description="主播UID")
    uname: str = Field(..., description="主播用户名")
    face: Optional[str] = Field(None, description="主播头像URL")
    gender: Optional[str] = Field(None, description="主播性别")
    level: Optional[int] = Field(None, description="主播等级")
    

class RoomDetail(RoomInfoBase):
    """房间详细信息"""
    short_id: Optional[int] = Field(None, description="短房间号")
    title: str = Field(..., description="直播间标题")
    live_status: LiveStatus = Field(..., description="直播状态")
    anchor_info: AnchorInfo = Field(..., description="主播信息")
    area_id: int = Field(..., description="分区ID")
    area_name: str = Field(..., description="分区名称")
    parent_area_id: int = Field(..., description="父分区ID")
    parent_area_name: str = Field(..., description="父分区名称")
    cover: Optional[str] = Field(None, description="直播间封面URL")
    tags: Optional[str] = Field(None, description="标签")
    description: Optional[str] = Field(None, description="房间描述")
    attention: Optional[int] = Field(None, description="关注数")
    

class RoomInfoResponse(BaseModel):
    """房间信息响应"""
    code: int = Field(0, description="状态码")
    message: str = Field("success", description="状态消息")
    data: RoomDetail = Field(..., description="房间详细信息")


class RoomConnectionStatus(BaseModel):
    """房间连接状态"""
    room_id: int = Field(..., description="房间ID")
    connected: bool = Field(..., description="是否已连接")
    connect_time: Optional[datetime] = Field(None, description="连接时间")
    danmaku_count: int = Field(0, description="接收到的弹幕数量")
    gift_count: int = Field(0, description="接收到的礼物数量")
    

class RoomConnectionResponse(BaseModel):
    """房间连接响应"""
    code: int = Field(0, description="状态码")
    message: str = Field("success", description="状态消息")
    data: RoomConnectionStatus = Field(..., description="连接状态")


class RoomListResponse(BaseModel):
    """房间列表响应"""
    code: int = Field(0, description="状态码")
    message: str = Field("success", description="状态消息")
    data: List[RoomConnectionStatus] = Field(..., description="房间连接状态列表") 