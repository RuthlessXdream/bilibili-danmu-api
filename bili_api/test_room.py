#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import sys
import logging
from datetime import datetime

import aiohttp

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 测试配置
API_BASE_URL = "http://0.0.0.0:8000/api/v1"
TEST_ROOM_ID = 31025025  # 要测试的房间ID


async def test_room_info():
    """测试获取房间信息"""
    url = f"{API_BASE_URL}/rooms/{TEST_ROOM_ID}"
    
    async with aiohttp.ClientSession() as session:
        try:
            logger.info(f"获取房间 {TEST_ROOM_ID} 信息...")
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"房间信息获取成功: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    return data
                else:
                    logger.error(f"获取房间信息失败: HTTP {resp.status}")
                    text = await resp.text()
                    logger.error(f"错误信息: {text}")
                    return None
        except Exception as e:
            logger.error(f"请求异常: {e}")
            return None


async def test_connect_room():
    """测试连接到房间"""
    url = f"{API_BASE_URL}/rooms/{TEST_ROOM_ID}/connect"
    
    async with aiohttp.ClientSession() as session:
        try:
            logger.info(f"连接到房间 {TEST_ROOM_ID}...")
            async with session.post(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"房间连接成功: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    return data
                else:
                    logger.error(f"连接房间失败: HTTP {resp.status}")
                    text = await resp.text()
                    logger.error(f"错误信息: {text}")
                    return None
        except Exception as e:
            logger.error(f"请求异常: {e}")
            return None


async def test_websocket():
    """测试WebSocket连接"""
    url = f"ws://0.0.0.0:8000/api/v1/ws/rooms/{TEST_ROOM_ID}"
    
    try:
        logger.info(f"连接WebSocket: {url}")
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url) as ws:
                logger.info("WebSocket连接成功，等待消息...")
                
                # 接收30秒的消息
                start_time = datetime.now()
                message_count = 0
                
                while (datetime.now() - start_time).total_seconds() < 30:
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=1.0)
                        
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            message_count += 1
                            data = json.loads(msg.data)
                            event_type = data.get("event")
                            
                            if event_type == "danmaku":
                                content = data.get("data", {}).get("content", "")
                                uname = data.get("data", {}).get("uname", "")
                                logger.info(f"弹幕: {uname} - {content}")
                            elif event_type == "gift":
                                gift_name = data.get("data", {}).get("gift_name", "")
                                uname = data.get("data", {}).get("uname", "")
                                count = data.get("data", {}).get("gift_count", 0)
                                logger.info(f"礼物: {uname} 赠送了 {count}个{gift_name}")
                            elif event_type == "heartbeat":
                                popularity = data.get("data", {}).get("popularity", 0)
                                logger.info(f"心跳: 人气值 {popularity}")
                            else:
                                logger.info(f"其他消息: {event_type}")
                        
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            logger.warning("WebSocket连接已关闭")
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"WebSocket错误: {msg.data}")
                            break
                    
                    except asyncio.TimeoutError:
                        # 超时，继续循环
                        continue
                
                logger.info(f"共接收到 {message_count} 条消息")
    
    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}")


async def main():
    """主函数"""
    logger.info(f"开始测试房间 {TEST_ROOM_ID}")
    
    # 1. 测试连接房间
    connect_result = await test_connect_room()
    if not connect_result:
        logger.error("连接房间测试失败，退出")
        return
    
    # 2. 测试获取房间信息
    room_info = await test_room_info()
    if not room_info:
        logger.error("获取房间信息测试失败")
    
    # 3. 测试WebSocket连接
    await test_websocket()
    
    logger.info("测试完成")


if __name__ == "__main__":
    asyncio.run(main()) 