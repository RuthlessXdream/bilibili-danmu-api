# B站直播弹幕API服务文档

本文档详细说明了B站直播弹幕API服务的所有端点、请求参数和响应格式。

## 基础信息

- 基础URL: `http://localhost:3100`
- 所有API响应均为JSON格式
- 标准响应格式:
  ```json
  {
    "status": "success|error",
    "message": "描述信息",
    "data": {} // 可选，返回的数据
  }
  ```

## API端点

### 健康检查

检查API服务是否正常运行。

- **URL**: `/api/health`
- **方法**: `GET`
- **响应示例**:
  ```json
  {
    "status": "success",
    "message": "Service is running"
  }
  ```

### Cookie管理

B站直播弹幕API支持两种Cookie管理方式：多账号Cookie管理和默认Cookie管理。

#### 多账号Cookie管理

##### 获取所有Cookie列表

获取所有已保存的Cookie列表（出于安全考虑，不会返回完整Cookie内容）。

- **URL**: `/api/cookies`
- **方法**: `GET`
- **响应示例**:
  ```json
  {
    "status": "success",
    "data": [
      {
        "id": "main",
        "has_bili_jct": true,
        "has_sessdata": true,
        "updated_at": "2023-05-20T15:30:45Z"
      },
      {
        "id": "alt_account",
        "has_bili_jct": true,
        "has_sessdata": true,
        "updated_at": "2023-05-21T10:15:22Z"
      }
    ]
  }
  ```

##### 添加新Cookie

添加一个新的Cookie并关联一个唯一ID。

- **URL**: `/api/cookies`
- **方法**: `POST`
- **请求体**:
  ```json
  {
    "id": "main", // 必填，Cookie唯一标识
    "cookie": "你的B站Cookie" // 必填，必须包含bili_jct和SESSDATA
  }
  ```
- **响应示例**:
  ```json
  {
    "status": "success",
    "message": "Cookie added successfully",
    "data": {
      "id": "main"
    }
  }
  ```

##### 获取指定Cookie

获取指定ID的Cookie完整内容。

- **URL**: `/api/cookies/:cookieID`
- **方法**: `GET`
- **URL参数**:
  - `cookieID`: Cookie的ID，必填
- **响应示例**:
  ```json
  {
    "status": "success",
    "data": {
      "id": "main",
      "cookie": "你的B站Cookie"
    }
  }
  ```

##### 更新指定Cookie

更新指定ID的Cookie内容。

- **URL**: `/api/cookies/:cookieID`
- **方法**: `PUT`
- **URL参数**:
  - `cookieID`: Cookie的ID，必填
- **请求体**:
  ```json
  {
    "cookie": "你的新B站Cookie" // 必填，必须包含bili_jct和SESSDATA
  }
  ```
- **响应示例**:
  ```json
  {
    "status": "success",
    "message": "Cookie updated successfully"
  }
  ```

##### 删除指定Cookie

删除指定ID的Cookie。

- **URL**: `/api/cookies/:cookieID`
- **方法**: `DELETE`
- **URL参数**:
  - `cookieID`: Cookie的ID，必填
- **响应示例**:
  ```json
  {
    "status": "success",
    "message": "Cookie deleted successfully"
  }
  ```

#### 默认Cookie管理（向后兼容）

##### 设置默认Cookie

设置全局默认Cookie，当连接直播间没有指定Cookie时，将使用此默认Cookie。

- **URL**: `/api/cookie/default`
- **方法**: `POST`
- **请求体**:
  ```json
  {
    "cookie": "你的B站Cookie" // 必填
  }
  ```
- **响应示例**:
  ```json
  {
    "status": "success",
    "message": "Default cookie set"
  }
  ```

##### 获取默认Cookie

获取当前设置的默认Cookie。

- **URL**: `/api/cookie/default`
- **方法**: `GET`
- **响应示例**:
  ```json
  {
    "status": "success",
    "cookie": "你的B站Cookie"
  }
  ```

### 连接直播间

连接到指定的B站直播间。

- **URL**: `/api/rooms/:roomID/connect`
- **方法**: `POST`
- **URL参数**:
  - `roomID`: B站直播间ID，必填
- **查询参数**:
  - `cookie`: B站Cookie，可选，提供后可获取更完整的弹幕信息。
  - `cookieID`: Cookie ID，可选，指定要使用的已保存Cookie的ID。
  - 优先级：如果指定了`cookieID`且存在，则使用该Cookie；如果提供了`cookie`参数，则使用该参数；如果都未提供且已设置默认Cookie，则使用默认Cookie。
- **响应示例**:
  ```json
  {
    "status": "success",
    "message": "Connected to room",
    "roomID": 31025025
  }
  ```

### 断开直播间连接

断开与指定直播间的连接。

- **URL**: `/api/rooms/:roomID/disconnect`
- **方法**: `POST`
- **URL参数**:
  - `roomID`: B站直播间ID，必填
- **响应示例**:
  ```json
  {
    "status": "success",
    "message": "Disconnected from room",
    "roomID": 31025025
  }
  ```

### 获取已连接的房间列表

获取当前已连接的所有直播间列表。

- **URL**: `/api/rooms/`
- **方法**: `GET`
- **响应示例**:
  ```json
  {
    "status": "success",
    "rooms": [
      {
        "roomID": 31025025,
        "status": "connected"
      }
    ]
  }
  ```

### 获取房间信息

获取指定直播间的详细信息。

- **URL**: `/api/rooms/:roomID/info`
- **方法**: `GET`
- **URL参数**:
  - `roomID`: B站直播间ID，必填
- **响应示例**:
  ```json
  {
    "status": "success",
    "data": {
      "code": 0,
      "msg": "ok",
      "message": "ok",
      "data": {
        "room_id": 31025025,
        "short_id": 0,
        "uid": 3546558758914330,
        "need_p2p": 0,
        "is_hidden": false,
        "is_locked": false,
        "is_portrait": false,
        "live_status": 1,
        "hidden_till": 0,
        "lock_till": 0,
        "encrypted": false,
        "pwd_verified": false,
        "live_time": 1751725415,
        "room_shield": 0,
        "is_sp": 0,
        "special_type": 0
      }
    }
  }
  ```

### 更新房间Cookie

更新指定直播间的Cookie。

- **URL**: `/api/rooms/:roomID/cookie`
- **方法**: `POST`
- **URL参数**:
  - `roomID`: B站直播间ID，必填
- **请求体**:
  ```json
  {
    "cookie": "你的B站Cookie" // 必填
  }
  ```
- **响应示例**:
  ```json
  {
    "status": "success",
    "message": "Cookie updated",
    "roomID": 31025025
  }
  ```

### 发送弹幕

向指定直播间发送弹幕。

- **URL**: `/api/rooms/:roomID/danmaku`
- **方法**: `POST`
- **URL参数**:
  - `roomID`: B站直播间ID，必填
- **请求体**:
  ```json
  {
    "message": "弹幕内容", // 必填
    "cookie": "你的B站Cookie", // 必填，需包含bili_jct和SESSDATA
    "color": "16777215", // 可选，弹幕颜色，默认为白色
    "fontSize": "25", // 可选，字体大小，默认为25
    "mode": "1", // 可选，弹幕模式，默认为1
    "isEmoticon": "0" // 可选，是否为表情弹幕，0为否，1为是，默认为0
  }
  ```
- **响应示例**:
  ```json
  {
    "status": "success",
    "message": "Danmaku sent",
    "data": {
      "code": 0,
      "message": "",
      "data": {}
    }
  }
  ```

### WebSocket连接

通过WebSocket实时接收直播间的弹幕、礼物等信息。

- **URL**: `/api/rooms/:roomID/ws`
- **方法**: `WebSocket`
- **URL参数**:
  - `roomID`: B站直播间ID，必填
- **消息格式**:
  ```json
  {
    "event": "事件类型",
    "data": {} // 事件数据
  }
  ```

#### 事件类型

1. **danmaku**: 普通弹幕
   ```json
   {
     "event": "danmaku",
     "data": {
       "user": {
         "uid": 12345678,
         "username": "用户名",
         "is_admin": false,
         "user_level": 10,
         "guard_level": 0,
         "medal": {
           "name": "勋章名称",
           "level": 10,
           "color": 16777215,
           "up_name": "UP主名称",
           "up_room_id": 12345678,
           "up_uid": 12345678
         }
       },
       "content": {
         "message": "弹幕内容",
         "type": 0
       },
       "timestamp": 1625123456,
       "raw": {} // 原始数据
     }
   }
   ```

2. **superchat**: 醒目留言(SC)
   ```json
   {
     "event": "superchat",
     "data": {
       "uid": 12345678,
       "user": "用户名",
       "price": 30,
       "message": "SC内容",
       "start_time": 1625123456,
       "end_time": 1625123556,
       "guard_level": 0,
       "user_level": 10,
       "face": "头像URL"
     }
   }
   ```

3. **gift**: 礼物
   ```json
   {
     "event": "gift",
     "data": {
       "uid": 12345678,
       "username": "用户名",
       "gift_id": 1,
       "gift_name": "礼物名称",
       "price": 100,
       "num": 1,
       "total_coin": 100,
       "guard_level": 0
     }
   }
   ```

4. **guard**: 上舰
   ```json
   {
     "event": "guard",
     "data": {
       "uid": 12345678,
       "username": "用户名",
       "guard_level": 3,
       "price": 198000,
       "gift_id": 10003,
       "gift_name": "舰长",
       "start_time": 1625123456,
       "end_time": 1625123556
     }
   }
   ```

5. **live_start**: 开播
   ```json
   {
     "event": "live_start",
     "data": {
       "room_id": 31025025,
       "time": "1625123456"
     }
   }
   ```

6. **live_end**: 下播
   ```json
   {
     "event": "live_end",
     "data": {
       "room_id": 31025025,
       "time": "1625123456"
     }
   }
   ```

## 错误码

| 状态码 | 描述 |
|--------|------|
| 200    | 请求成功 |
| 400    | 请求参数错误 |
| 404    | 资源不存在 |
| 500    | 服务器内部错误 |

## 使用示例

### 设置默认Cookie

```bash
curl -X POST "http://localhost:8081/api/cookie/default" \
  -H "Content-Type: application/json" \
  -d '{"cookie": "buvid3=xxx; SESSDATA=xxx; bili_jct=xxx"}'
```

### 使用curl连接直播间

```bash
curl -X POST "http://localhost:8081/api/rooms/31025025/connect"
```

### 更新直播间Cookie

```bash
curl -X POST "http://localhost:8081/api/rooms/31025025/cookie" \
  -H "Content-Type: application/json" \
  -d '{"cookie": "buvid3=xxx; SESSDATA=xxx; bili_jct=xxx"}'
```

### 使用curl获取房间信息

```bash
curl "http://localhost:8081/api/rooms/31025025/info"
```

### 使用JavaScript连接WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8081/api/rooms/31025025/ws');

ws.onopen = () => {
  console.log('连接成功');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.event) {
    case 'danmaku':
      console.log(`[弹幕] ${data.data.user.username}: ${data.data.content.message}`);
      break;
    case 'superchat':
      console.log(`[SC|${data.data.price}元] ${data.data.user}: ${data.data.message}`);
      break;
    case 'gift':
      console.log(`[礼物] ${data.data.username} 的 ${data.data.gift_name} ${data.data.num}个`);
      break;
    case 'guard':
      console.log(`[大航海] ${data.data.username} 开通了舰长`);
      break;
  }
};

ws.onclose = () => {
  console.log('连接关闭');
};
```

## 注意事项

1. B站API可能随时变化，如遇问题请更新依赖库
2. 非登录状态下获取的弹幕信息可能不完整
3. 长时间使用时请妥善处理WebSocket连接的重连
4. 发送弹幕需要有效的B站Cookie，包含bili_jct和SESSDATA 