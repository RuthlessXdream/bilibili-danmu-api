# B站直播弹幕 API

基于 [blivedm](https://github.com/xfgryujk/blivedm) 库开发的 B站直播弹幕 API 服务，提供 RESTful API 和 WebSocket 接口，用于获取 B站直播间的实时数据。

## 特性

- **RESTful API**: 获取房间信息、连接/断开房间、查询已连接房间列表
- **WebSocket**: 实时接收直播间弹幕、礼物、上舰等消息
- **高性能**: 基于 FastAPI 和 asyncio 的高性能异步实现
- **高可靠**: 自动重连机制，确保数据连续性
- **可扩展**: 模块化设计，易于扩展
- **低耦合**: 与 blivedm 库保持解耦，不修改原始依赖包

## 安装

1. 克隆项目
```bash
git clone https://github.com/your-username/bili-api.git
cd bili-api
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法

### 启动服务

```bash
cd bili_api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API 文档

启动服务后，访问以下链接查看API文档：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 主要接口

#### RESTful API

- `GET /api/v1/rooms/{room_id}` - 获取房间信息
- `POST /api/v1/rooms/{room_id}/connect` - 连接房间
- `POST /api/v1/rooms/{room_id}/disconnect` - 断开房间连接
- `GET /api/v1/rooms` - 获取所有已连接房间

#### WebSocket

- `WebSocket /api/v1/ws/rooms/{room_id}` - 通过WebSocket接收房间实时消息

## 前端集成示例

### Next.js + TypeScript 集成示例

1. 创建房间连接API客户端:

```typescript
// services/biliApi.ts
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_BILI_API_URL || 'http://localhost:8000/api/v1';

export interface RoomInfo {
  room_id: number;
  title: string;
  live_status: {
    live_status: number;
    online: number;
  };
  // ... 其他字段
}

export interface ConnectionStatus {
  room_id: number;
  connected: boolean;
  connect_time: string;
  danmaku_count: number;
  gift_count: number;
}

// 获取房间信息
export const getRoomInfo = async (roomId: number): Promise<RoomInfo> => {
  const response = await axios.get(`${API_BASE_URL}/rooms/${roomId}`);
  return response.data.data;
};

// 连接房间
export const connectRoom = async (roomId: number, cookies?: string): Promise<ConnectionStatus> => {
  const response = await axios.post(`${API_BASE_URL}/rooms/${roomId}/connect`, {
    room_id: roomId,
    cookies,
    auto_reconnect: true
  });
  return response.data.data;
};

// 断开房间连接
export const disconnectRoom = async (roomId: number): Promise<void> => {
  await axios.post(`${API_BASE_URL}/rooms/${roomId}/disconnect`);
};

// 获取所有已连接房间
export const getAllRooms = async (): Promise<ConnectionStatus[]> => {
  const response = await axios.get(`${API_BASE_URL}/rooms`);
  return response.data.data;
};
```

2. 创建WebSocket连接钩子:

```typescript
// hooks/useRoomWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react';

export interface DanmakuMessage {
  uid: number;
  uname: string;
  content: string;
  // ... 其他字段
}

export interface GiftMessage {
  uid: number;
  uname: string;
  gift_name: string;
  gift_count: number;
  price: number;
  total_coin: number;
  // ... 其他字段
}

type MessageHandler<T> = (message: T) => void;

export const useRoomWebSocket = (roomId: number) => {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  
  // 消息处理器
  const messageHandlers = useRef<{
    [key: string]: MessageHandler<any>[]
  }>({});
  
  // 添加消息处理器
  const addMessageHandler = useCallback(<T>(eventType: string, handler: MessageHandler<T>) => {
    if (!messageHandlers.current[eventType]) {
      messageHandlers.current[eventType] = [];
    }
    messageHandlers.current[eventType].push(handler);
    
    return () => {
      const handlers = messageHandlers.current[eventType];
      const index = handlers.indexOf(handler);
      if (index !== -1) {
        handlers.splice(index, 1);
      }
    };
  }, []);
  
  // 连接WebSocket
  useEffect(() => {
    if (!roomId) return;
    
    const API_BASE_URL = process.env.NEXT_PUBLIC_BILI_API_URL || 'http://localhost:8000/api/v1';
    const wsUrl = `${API_BASE_URL.replace(/^http/, 'ws')}/ws/rooms/${roomId}`;
    
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;
    
    socket.onopen = () => {
      setIsConnected(true);
      setError(null);
      console.log(`WebSocket connected to room ${roomId}`);
    };
    
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        const eventType = message.event;
        
        // 调用对应的消息处理器
        if (messageHandlers.current[eventType]) {
          messageHandlers.current[eventType].forEach(handler => {
            handler(message.data);
          });
        }
        
        // 调用全局消息处理器
        if (messageHandlers.current['*']) {
          messageHandlers.current['*'].forEach(handler => {
            handler(message);
          });
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };
    
    socket.onerror = (err) => {
      setError(err as any);
      console.error('WebSocket error:', err);
    };
    
    socket.onclose = () => {
      setIsConnected(false);
      console.log(`WebSocket disconnected from room ${roomId}`);
    };
    
    return () => {
      socket.close();
    };
  }, [roomId]);
  
  // 添加弹幕处理器
  const onDanmaku = useCallback((handler: MessageHandler<DanmakuMessage>) => {
    return addMessageHandler('danmaku', handler);
  }, [addMessageHandler]);
  
  // 添加礼物处理器
  const onGift = useCallback((handler: MessageHandler<GiftMessage>) => {
    return addMessageHandler('gift', handler);
  }, [addMessageHandler]);
  
  return {
    isConnected,
    error,
    onDanmaku,
    onGift,
    // 可以添加更多特定类型的处理器
    addMessageHandler
  };
};
```

3. 在组件中使用:

```tsx
// components/LiveRoom.tsx
import { useState, useEffect } from 'react';
import { getRoomInfo, connectRoom, disconnectRoom } from '../services/biliApi';
import { useRoomWebSocket } from '../hooks/useRoomWebSocket';

interface LiveRoomProps {
  roomId: number;
}

export const LiveRoom: React.FC<LiveRoomProps> = ({ roomId }) => {
  const [roomInfo, setRoomInfo] = useState(null);
  const [danmakus, setDanmakus] = useState<any[]>([]);
  const [gifts, setGifts] = useState<any[]>([]);
  
  const { isConnected, error, onDanmaku, onGift } = useRoomWebSocket(roomId);
  
  // 获取房间信息
  useEffect(() => {
    const fetchRoomInfo = async () => {
      try {
        const info = await getRoomInfo(roomId);
        setRoomInfo(info);
      } catch (err) {
        console.error('Failed to fetch room info:', err);
      }
    };
    
    fetchRoomInfo();
  }, [roomId]);
  
  // 连接房间
  useEffect(() => {
    const connect = async () => {
      try {
        await connectRoom(roomId);
        console.log(`Connected to room ${roomId}`);
      } catch (err) {
        console.error('Failed to connect to room:', err);
      }
    };
    
    connect();
    
    return () => {
      disconnectRoom(roomId).catch(err => {
        console.error('Failed to disconnect from room:', err);
      });
    };
  }, [roomId]);
  
  // 监听弹幕
  useEffect(() => {
    const unsubscribe = onDanmaku((message) => {
      setDanmakus(prev => [...prev.slice(-99), message]);
    });
    
    return unsubscribe;
  }, [onDanmaku]);
  
  // 监听礼物
  useEffect(() => {
    const unsubscribe = onGift((message) => {
      setGifts(prev => [...prev.slice(-19), message]);
    });
    
    return unsubscribe;
  }, [onGift]);
  
  if (!roomInfo) {
    return <div>Loading...</div>;
  }
  
  return (
    <div>
      <h1>{roomInfo.title}</h1>
      <div>
        <p>直播状态: {roomInfo.live_status.live_status === 1 ? '直播中' : '未开播'}</p>
        <p>在线人数: {roomInfo.live_status.online}</p>
      </div>
      
      <div className="danmaku-container">
        <h2>弹幕列表</h2>
        <ul>
          {danmakus.map((danmaku, index) => (
            <li key={index}>
              {danmaku.uname}: {danmaku.content}
            </li>
          ))}
        </ul>
      </div>
      
      <div className="gift-container">
        <h2>礼物列表</h2>
        <ul>
          {gifts.map((gift, index) => (
            <li key={index}>
              {gift.uname} 赠送 {gift.gift_name} x{gift.gift_count} (价值: {gift.total_coin}瓜子)
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
```

## 许可证

MIT License

## 鸣谢

- [blivedm](https://github.com/xfgryujk/blivedm) - B站直播弹幕库 