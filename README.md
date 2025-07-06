# B站直播弹幕API服务

这是一个基于[blivedm-go](https://github.com/Akegarasu/blivedm-go)库的RESTful API服务，用于连接、管理和监听B站直播间弹幕。

## 功能特点

- 连接多个B站直播间，实时接收弹幕数据
- 通过WebSocket推送实时弹幕数据
- 支持弹幕、醒目留言(SC)、礼物、上舰等多种消息类型
- 支持发送弹幕到直播间
- 获取直播间信息
- 多账号Cookie管理，支持增删查改
- RESTful API设计，易于集成

## 最近更新

- 服务端口从8081迁移到3100
- 增强Cookie管理功能，支持多账号Cookie的增删查改
- 改进启动/停止脚本，增加自动环境检查和编译功能
- 增加`--all`选项用于停止所有服务实例

## 安装

### 前置条件

- Go 1.16+

### 克隆仓库

```bash
git clone https://github.com/RuthlessXdream/bilibili-danmu-api.git
cd bilibili-danmu-api
```

### 安装依赖并编译

方法1：使用启动脚本自动安装依赖并编译
```bash
chmod +x start.sh
./start.sh --deps --build
```

方法2：手动安装依赖并编译
```bash
go mod tidy
go build -o danmu-api
```

## 使用方法

### 启动服务

```bash
./start.sh
```

默认配置：
- 端口：3100
- 日志级别：info
- 日志文件：api.log

自定义配置：
```bash
./start.sh --port 8080 --log-level debug --log-file custom.log
```

### 停止服务

停止指定端口的服务：
```bash
./stop.sh --port 3100
```

停止所有服务实例：
```bash
./stop.sh --all
```

### API端点

#### 健康检查

```
GET /api/health
```

#### Cookie管理

##### 添加Cookie
```
POST /api/cookies
```

请求体(JSON):
```json
{
  "id": "main",
  "cookie": "你的B站Cookie"
}
```

##### 获取所有Cookie
```
GET /api/cookies
```

##### 获取指定Cookie
```
GET /api/cookies/:cookieID
```

##### 更新Cookie
```
PUT /api/cookies/:cookieID
```

请求体(JSON):
```json
{
  "cookie": "你的新B站Cookie"
}
```

##### 删除Cookie
```
DELETE /api/cookies/:cookieID
```

#### 连接直播间

```
POST /api/rooms/:roomID/connect
```

查询参数:
- `cookie`: (可选) B站登录后的Cookie
- `cookieID`: (可选) 指定要使用的已保存Cookie的ID

#### 断开直播间连接

```
POST /api/rooms/:roomID/disconnect
```

#### 获取已连接的房间列表

```
GET /api/rooms/
```

#### 获取房间信息

```
GET /api/rooms/:roomID/info
```

#### 发送弹幕

```
POST /api/rooms/:roomID/danmaku
```

请求体(JSON):
```json
{
  "message": "弹幕内容",
  "cookie": "你的B站Cookie",
  "color": "16777215",
  "fontSize": "25",
  "mode": "1",
  "isEmoticon": "0"
}
```

#### WebSocket连接

```
WS /api/rooms/:roomID/ws
```

WebSocket事件类型：
- `danmaku`: 普通弹幕
- `superchat`: 醒目留言
- `gift`: 礼物
- `guard`: 上舰
- `live_start`: 开播
- `live_end`: 下播

## 示例

### 连接直播间

```bash
curl -X POST "http://localhost:3100/api/rooms/31025025/connect"
```

### 使用指定Cookie连接房间

```bash
curl -X POST "http://localhost:3100/api/rooms/31025025/connect?cookieID=main"
```

### 获取房间列表

```bash
curl "http://localhost:3100/api/rooms/"
```

### Cookie管理示例

#### 添加Cookie

```bash
curl -X POST "http://localhost:3100/api/cookies" \
  -H "Content-Type: application/json" \
  -d '{"id": "main", "cookie": "your_cookie_string"}'
```

#### 使用指定Cookie连接房间

```bash
curl -X POST "http://localhost:3100/api/rooms/31025025/connect?cookieID=main"
```

#### 获取所有Cookie

```bash
curl "http://localhost:3100/api/cookies"
```

#### 更新Cookie

```bash
curl -X PUT "http://localhost:3100/api/cookies/main" \
  -H "Content-Type: application/json" \
  -d '{"cookie": "your_new_cookie_string"}'
```

#### 删除Cookie

```bash
curl -X DELETE "http://localhost:3100/api/cookies/main"
```

### WebSocket客户端示例(JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:3100/api/rooms/31025025/ws');

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

## 详细文档

完整API文档请参阅 [API_DOC.md](API_DOC.md)。

## 注意事项

- B站API可能随时变化，如遇问题请更新依赖库
- 非登录状态下获取的弹幕信息可能不完整
- 长时间使用时请妥善处理WebSocket连接的重连
- 请勿滥用API，遵守B站相关规定

## 许可证

MIT License 