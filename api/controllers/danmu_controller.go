package controllers

import (
	"net/http"
	"strconv"
	"sync"
	"time"

	"github.com/Akegarasu/blivedm-go/api"
	"github.com/Akegarasu/blivedm-go/client"
	"github.com/Akegarasu/blivedm-go/message"
	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	log "github.com/sirupsen/logrus"
)

// 全局默认Cookie
var DefaultCookie string = ""

// 添加Cookie管理结构
type CookieManager struct {
	Cookies map[string]string // 使用cookieID作为键，cookie字符串作为值
	mu      sync.RWMutex
}

// 初始化全局Cookie管理器
var GlobalCookieManager = &CookieManager{
	Cookies: make(map[string]string),
}

// DanmuClientManager 管理多个直播间的弹幕客户端
type DanmuClientManager struct {
	Clients map[int]*DanmuClient
	mutex   sync.RWMutex
}

// DanmuClient 包装每个直播间的客户端
type DanmuClient struct {
	Client      *client.Client
	RoomID      int
	Cookie      string
	WSClients   map[*websocket.Conn]bool
	WSClientsMx sync.RWMutex
	Status      string // "connected", "disconnected", "connecting"
	ConnectedAt time.Time
}

// NewDanmuClientManager 创建一个新的弹幕客户端管理器
func NewDanmuClientManager() *DanmuClientManager {
	return &DanmuClientManager{
		Clients: make(map[int]*DanmuClient),
		mutex:   sync.RWMutex{},
	}
}

// Global danmu client manager
var Manager = NewDanmuClientManager()

// WebSocket连接升级器
var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		return true // 允许所有来源的连接
	},
}

// ConnectRoom 连接到指定房间
func ConnectRoom(c *gin.Context) {
	// 获取房间ID
	roomIDStr := c.Param("roomID")
	roomID64, err := strconv.ParseUint(roomIDStr, 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid room ID"})
		return
	}
	roomID := int(roomID64)

	// 获取Cookie参数
	cookie := c.Query("cookie")
	cookieID := c.Query("cookieID")

	// 优先使用指定ID的Cookie
	if cookieID != "" {
		GlobalCookieManager.mu.RLock()
		if storedCookie, exists := GlobalCookieManager.Cookies[cookieID]; exists {
			cookie = storedCookie
		}
		GlobalCookieManager.mu.RUnlock()
	}

	// 如果没有提供cookie但有默认cookie，则使用默认cookie
	if cookie == "" && DefaultCookie != "" {
		cookie = DefaultCookie
	}

	// 检查房间是否已经连接
	Manager.mutex.RLock()
	danmuClient, exists := Manager.Clients[roomID]
	Manager.mutex.RUnlock()

	if exists && danmuClient.Status == "connected" {
		c.JSON(http.StatusOK, gin.H{
			"status":  "success",
			"message": "Room already connected",
			"roomID":  roomID,
		})
		return
	}

	// 创建新的弹幕客户端
	newClient := client.NewClient(roomID)
	if cookie != "" {
		newClient.SetCookie(cookie)
	}

	// 创建包装客户端
	danmuClient = &DanmuClient{
		Client:      newClient,
		RoomID:      roomID,
		Cookie:      cookie,
		WSClients:   make(map[*websocket.Conn]bool),
		Status:      "connecting",
		ConnectedAt: time.Now(),
	}

	// 添加到管理器
	Manager.mutex.Lock()
	Manager.Clients[roomID] = danmuClient
	Manager.mutex.Unlock()

	// 设置消息处理器
	setupMessageHandlers(danmuClient)

	// 启动客户端
	err = danmuClient.Client.Start()
	if err != nil {
		Manager.mutex.Lock()
		delete(Manager.Clients, roomID)
		Manager.mutex.Unlock()
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to connect to room: " + err.Error()})
		return
	}

	danmuClient.Status = "connected"
	c.JSON(http.StatusOK, gin.H{
		"status":  "success",
		"message": "Connected to room",
		"roomID":  roomID,
	})
}

// DisconnectRoom 断开与指定房间的连接
func DisconnectRoom(c *gin.Context) {
	roomIDStr := c.Param("roomID")
	roomID, err := strconv.Atoi(roomIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid room ID"})
		return
	}

	Manager.mutex.RLock()
	danmuClient, exists := Manager.Clients[roomID]
	Manager.mutex.RUnlock()

	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "Room not connected"})
		return
	}

	// 关闭所有WebSocket连接
	danmuClient.WSClientsMx.Lock()
	for conn := range danmuClient.WSClients {
		conn.Close()
	}
	danmuClient.WSClientsMx.Unlock()

	// 停止客户端
	danmuClient.Client.Stop()
	danmuClient.Status = "disconnected"

	// 从管理器中移除
	Manager.mutex.Lock()
	delete(Manager.Clients, roomID)
	Manager.mutex.Unlock()

	c.JSON(http.StatusOK, gin.H{
		"status":  "success",
		"message": "Disconnected from room",
		"roomID":  roomID,
	})
}

// ListRooms 列出所有已连接的房间
func ListRooms(c *gin.Context) {
	Manager.mutex.RLock()
	defer Manager.mutex.RUnlock()

	rooms := make([]map[string]interface{}, 0)
	for roomID, client := range Manager.Clients {
		rooms = append(rooms, map[string]interface{}{
			"roomID": roomID,
			"status": client.Status,
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"status": "success",
		"rooms":  rooms,
	})
}

// GetRoomInfo 获取房间信息
func GetRoomInfo(c *gin.Context) {
	roomIDStr := c.Param("roomID")
	roomID, err := strconv.Atoi(roomIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid room ID"})
		return
	}

	roomInfo, err := api.GetRoomInfo(roomID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get room info: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status": "success",
		"data":   roomInfo,
	})
}

// SendDanmaku 发送弹幕到指定房间
func SendDanmaku(c *gin.Context) {
	roomIDStr := c.Param("roomID")
	roomID, err := strconv.Atoi(roomIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid room ID"})
		return
	}

	var req struct {
		Message    string `json:"message" binding:"required"`
		Cookie     string `json:"cookie" binding:"required"`
		Color      string `json:"color"`
		FontSize   string `json:"fontSize"`
		Mode       string `json:"mode"`
		IsEmoticon string `json:"isEmoticon"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	// 从Cookie中提取bili_jct和SESSDATA
	var csrf, sessData string
	cookieParts := map[string]string{}
	for _, part := range SplitCookie(req.Cookie) {
		cookieParts[part.Key] = part.Value
	}
	csrf = cookieParts["bili_jct"]
	sessData = cookieParts["SESSDATA"]

	if csrf == "" || sessData == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid cookie: bili_jct or SESSDATA not found"})
		return
	}

	// 创建验证信息
	verify := &api.BiliVerify{
		Csrf:     csrf,
		SessData: sessData,
	}

	// 设置弹幕请求
	dmReq := &api.DanmakuRequest{
		Msg:      req.Message,
		RoomID:   strconv.Itoa(roomID),
		Bubble:   "0",
		Color:    getValidColor(req.Color),
		FontSize: getValidFontSize(req.FontSize),
		Mode:     getValidMode(req.Mode),
		DmType:   getValidDmType(req.IsEmoticon),
	}

	// 发送弹幕
	resp, err := api.SendDanmaku(dmReq, verify)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to send danmaku: " + err.Error()})
		return
	}

	if resp.Code != 0 {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error":   "Failed to send danmaku",
			"message": resp.Message,
			"code":    resp.Code,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  "success",
		"message": "Danmaku sent",
		"data":    resp,
	})
}

// WebSocketDanmaku 通过WebSocket实时接收弹幕
func WebSocketDanmaku(c *gin.Context) {
	roomIDStr := c.Param("roomID")
	roomID, err := strconv.Atoi(roomIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid room ID"})
		return
	}

	// 检查房间是否已经连接
	Manager.mutex.RLock()
	danmuClient, exists := Manager.Clients[roomID]
	Manager.mutex.RUnlock()

	if !exists || danmuClient.Status != "connected" {
		c.JSON(http.StatusNotFound, gin.H{"error": "Room not connected"})
		return
	}

	// 升级HTTP连接到WebSocket
	ws, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Errorf("Failed to set websocket upgrade: %+v", err)
		return
	}

	// 添加WebSocket客户端
	danmuClient.WSClientsMx.Lock()
	danmuClient.WSClients[ws] = true
	danmuClient.WSClientsMx.Unlock()

	// 处理WebSocket断开
	go func() {
		defer func() {
			ws.Close()
			danmuClient.WSClientsMx.Lock()
			delete(danmuClient.WSClients, ws)
			danmuClient.WSClientsMx.Unlock()
		}()

		for {
			_, _, err := ws.ReadMessage()
			if err != nil {
				break
			}
		}
	}()
}

// 设置消息处理器
func setupMessageHandlers(dc *DanmuClient) {
	// 监听弹幕
	dc.Client.OnDanmaku(func(danmaku *message.Danmaku) {
		data := formatDanmakuMessage(danmaku)
		broadcastToWSClients(dc, "danmaku", data)
	})

	// 监听醒目留言
	dc.Client.OnSuperChat(func(sc *message.SuperChat) {
		data := formatSuperChatMessage(sc)
		broadcastToWSClients(dc, "superchat", data)
	})

	// 监听礼物
	dc.Client.OnGift(func(gift *message.Gift) {
		if gift.CoinType == "gold" {
			data := formatGiftMessage(gift)
			broadcastToWSClients(dc, "gift", data)
		}
	})

	// 监听上舰
	dc.Client.OnGuardBuy(func(guardBuy *message.GuardBuy) {
		data := formatGuardBuyMessage(guardBuy)
		broadcastToWSClients(dc, "guard", data)
	})

	// 监听直播开始
	dc.Client.RegisterCustomEventHandler("LIVE", func(s string) {
		broadcastToWSClients(dc, "live_start", map[string]interface{}{
			"room_id": dc.RoomID,
			"time":    GetCurrentTime(),
		})
	})

	// 监听直播结束
	dc.Client.RegisterCustomEventHandler("PREPARING", func(s string) {
		broadcastToWSClients(dc, "live_end", map[string]interface{}{
			"room_id": dc.RoomID,
			"time":    GetCurrentTime(),
		})
	})
}

// 广播消息到所有WebSocket客户端
func broadcastToWSClients(dc *DanmuClient, eventType string, data interface{}) {
	message := map[string]interface{}{
		"event": eventType,
		"data":  data,
	}

	dc.WSClientsMx.RLock()
	defer dc.WSClientsMx.RUnlock()

	for client := range dc.WSClients {
		err := client.WriteJSON(message)
		if err != nil {
			log.Errorf("Error on websocket write: %v", err)
			client.Close()
			// 不要在这里从WSClients中删除客户端，因为会导致concurrent map iteration and map write错误
			// 删除操作会在读取goroutine中完成
		}
	}
}

// 格式化弹幕消息
func formatDanmakuMessage(danmaku *message.Danmaku) map[string]interface{} {
	// 构建用户信息
	userInfo := map[string]interface{}{
		"uid":         danmaku.Sender.Uid,
		"username":    danmaku.Sender.Uname,
		"is_admin":    danmaku.Sender.Admin,
		"user_level":  danmaku.Sender.UserLevel,
		"guard_level": danmaku.Sender.GuardLevel,
	}

	// 添加勋章信息（如果有）
	if danmaku.Sender.Medal != nil && danmaku.Sender.Medal.Level > 0 {
		userInfo["medal"] = map[string]interface{}{
			"name":       danmaku.Sender.Medal.Name,
			"level":      danmaku.Sender.Medal.Level,
			"color":      danmaku.Sender.Medal.Color,
			"up_name":    danmaku.Sender.Medal.UpName,
			"up_room_id": danmaku.Sender.Medal.UpRoomId,
			"up_uid":     danmaku.Sender.Medal.UpUid,
		}
	}

	// 构建消息内容
	content := map[string]interface{}{
		"message": danmaku.Content,
		"type":    danmaku.Type,
	}

	// 如果是表情弹幕，添加表情信息
	if danmaku.Type == message.EmoticonDanmaku {
		content["emoticon"] = map[string]interface{}{
			"url":    danmaku.Emoticon.Url,
			"width":  danmaku.Emoticon.Width,
			"height": danmaku.Emoticon.Height,
		}
	}

	return map[string]interface{}{
		"user":      userInfo,
		"content":   content,
		"timestamp": danmaku.Timestamp,
		"raw":       danmaku.Raw,
	}
}

// 格式化SC消息
func formatSuperChatMessage(sc *message.SuperChat) map[string]interface{} {
	return map[string]interface{}{
		"uid":         sc.Uid,
		"user":        sc.UserInfo.Uname,
		"price":       sc.Price,
		"message":     sc.Message,
		"start_time":  sc.StartTime,
		"end_time":    sc.EndTime,
		"guard_level": sc.UserInfo.GuardLevel,
		"user_level":  sc.UserInfo.UserLevel,
		"face":        sc.UserInfo.Face,
	}
}

// 格式化礼物消息
func formatGiftMessage(gift *message.Gift) map[string]interface{} {
	return map[string]interface{}{
		"uid":         gift.Uid,
		"username":    gift.Uname,
		"gift_id":     gift.GiftId,
		"gift_name":   gift.GiftName,
		"price":       gift.Price,
		"num":         gift.Num,
		"total_coin":  gift.TotalCoin,
		"guard_level": gift.GuardLevel,
	}
}

// 格式化舰长消息
func formatGuardBuyMessage(guardBuy *message.GuardBuy) map[string]interface{} {
	return map[string]interface{}{
		"uid":         guardBuy.Uid,
		"username":    guardBuy.Username,
		"guard_level": guardBuy.GuardLevel,
		"price":       guardBuy.Price,
		"gift_id":     guardBuy.GiftId,
		"gift_name":   guardBuy.GiftName,
		"start_time":  guardBuy.StartTime,
		"end_time":    guardBuy.EndTime,
	}
}

// 辅助函数

// CookiePart 表示Cookie的键值对
type CookiePart struct {
	Key   string
	Value string
}

// SplitCookie 将Cookie字符串分割成键值对
func SplitCookie(cookie string) []CookiePart {
	var parts []CookiePart
	for _, part := range splitCookieString(cookie) {
		kv := splitKeyValue(part)
		if len(kv) == 2 {
			parts = append(parts, CookiePart{Key: kv[0], Value: kv[1]})
		}
	}
	return parts
}

// splitCookieString 将Cookie字符串按分号分割
func splitCookieString(cookie string) []string {
	return splitAndTrim(cookie, ";")
}

// splitKeyValue 将键值对字符串按等号分割
func splitKeyValue(kv string) []string {
	return splitAndTrim(kv, "=")
}

// splitAndTrim 按指定分隔符分割字符串并去除空白
func splitAndTrim(s, sep string) []string {
	var result []string
	for _, part := range stringSplit(s, sep) {
		result = append(result, stringTrim(part))
	}
	return result
}

// stringSplit 字符串分割
func stringSplit(s, sep string) []string {
	result := make([]string, 0)
	for _, part := range stringSplitFunc(s, sep) {
		if part != "" {
			result = append(result, part)
		}
	}
	return result
}

// stringSplitFunc 字符串分割核心函数
func stringSplitFunc(s, sep string) []string {
	return stringSplitFuncImpl(s, sep)
}

// stringSplitFuncImpl 字符串分割实现
func stringSplitFuncImpl(s, sep string) []string {
	return stringSplitFuncWithSep(s, sep)
}

// stringSplitFuncWithSep 使用分隔符分割字符串
func stringSplitFuncWithSep(s, sep string) []string {
	return stringSplitFuncWithSepAndLimit(s, sep, -1)
}

// stringSplitFuncWithSepAndLimit 使用分隔符和限制分割字符串
func stringSplitFuncWithSepAndLimit(s, sep string, n int) []string {
	return stringsSplit(s, sep)
}

// stringsSplit 最终的字符串分割函数
func stringsSplit(s, sep string) []string {
	return stringSplitBasic(s, sep)
}

// stringSplitBasic 基本的字符串分割
func stringSplitBasic(s, sep string) []string {
	parts := []string{}
	for len(s) > 0 {
		idx := stringIndex(s, sep)
		if idx < 0 {
			parts = append(parts, s)
			break
		}
		parts = append(parts, s[:idx])
		s = s[idx+len(sep):]
	}
	return parts
}

// stringIndex 查找子串位置
func stringIndex(s, substr string) int {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return i
		}
	}
	return -1
}

// stringTrim 去除字符串两端的空白
func stringTrim(s string) string {
	return stringTrimImpl(s)
}

// stringTrimImpl 去除空白的实现
func stringTrimImpl(s string) string {
	return stringTrimSpace(s)
}

// stringTrimSpace 去除空白
func stringTrimSpace(s string) string {
	start, end := 0, len(s)
	for start < end && isSpace(s[start]) {
		start++
	}
	for start < end && isSpace(s[end-1]) {
		end--
	}
	if start == 0 && end == len(s) {
		return s
	}
	return s[start:end]
}

// isSpace 判断字符是否为空白
func isSpace(c byte) bool {
	return c == ' ' || c == '\t' || c == '\n' || c == '\r'
}

// 获取有效的颜色值
func getValidColor(color string) string {
	if color == "" {
		return "16777215" // 默认白色
	}
	return color
}

// 获取有效的字体大小
func getValidFontSize(fontSize string) string {
	if fontSize == "" {
		return "25" // 默认大小
	}
	return fontSize
}

// 获取有效的弹幕模式
func getValidMode(mode string) string {
	if mode == "" {
		return "1" // 默认模式
	}
	return mode
}

// 获取有效的弹幕类型
func getValidDmType(isEmoticon string) string {
	if isEmoticon == "1" {
		return "1" // 表情弹幕
	}
	return "0" // 普通弹幕
}

// 获取当前时间
func GetCurrentTime() string {
	return strconv.FormatInt(time.Now().Unix(), 10)
}

// UpdateCookie 更新指定房间的Cookie
func UpdateCookie(c *gin.Context) {
	roomIDStr := c.Param("roomID")
	roomID, err := strconv.Atoi(roomIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid room ID"})
		return
	}

	var req struct {
		Cookie string `json:"cookie" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	// 检查房间是否已经连接
	Manager.mutex.RLock()
	danmuClient, exists := Manager.Clients[roomID]
	Manager.mutex.RUnlock()

	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "Room not connected"})
		return
	}

	// 更新Cookie
	danmuClient.Cookie = req.Cookie
	danmuClient.Client.SetCookie(req.Cookie)

	c.JSON(http.StatusOK, gin.H{
		"status":  "success",
		"message": "Cookie updated",
		"roomID":  roomID,
	})
}

// SetDefaultCookie 设置默认Cookie
func SetDefaultCookie(c *gin.Context) {
	var req struct {
		Cookie string `json:"cookie" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	// 保存默认Cookie到全局变量
	DefaultCookie = req.Cookie

	c.JSON(http.StatusOK, gin.H{
		"status":  "success",
		"message": "Default cookie set",
	})
}

// GetDefaultCookie 获取默认Cookie
func GetDefaultCookie(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status": "success",
		"cookie": DefaultCookie,
	})
}

// ListCookies 列出所有可用的Cookie
func ListCookies(c *gin.Context) {
	GlobalCookieManager.mu.RLock()
	defer GlobalCookieManager.mu.RUnlock()

	// 准备返回数据，只返回ID和部分cookie信息（出于安全考虑）
	type CookieInfo struct {
		ID          string `json:"id"`
		HasBiliJct  bool   `json:"has_bili_jct"`
		HasSessData bool   `json:"has_sessdata"`
		UpdatedAt   string `json:"updated_at"`
	}

	cookieInfos := make([]CookieInfo, 0, len(GlobalCookieManager.Cookies))

	for id, cookieStr := range GlobalCookieManager.Cookies {
		parts := SplitCookie(cookieStr)
		hasBiliJct := false
		hasSessData := false

		for _, part := range parts {
			if part.Key == "bili_jct" {
				hasBiliJct = true
			}
			if part.Key == "SESSDATA" {
				hasSessData = true
			}
		}

		cookieInfos = append(cookieInfos, CookieInfo{
			ID:          id,
			HasBiliJct:  hasBiliJct,
			HasSessData: hasSessData,
			UpdatedAt:   time.Now().Format(time.RFC3339),
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"status": "success",
		"data":   cookieInfos,
	})
}

// GetCookie 获取指定ID的Cookie
func GetCookie(c *gin.Context) {
	cookieID := c.Param("cookieID")

	GlobalCookieManager.mu.RLock()
	defer GlobalCookieManager.mu.RUnlock()

	cookie, exists := GlobalCookieManager.Cookies[cookieID]
	if !exists {
		c.JSON(http.StatusNotFound, gin.H{
			"status":  "error",
			"message": "Cookie not found",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status": "success",
		"data": gin.H{
			"id":     cookieID,
			"cookie": cookie,
		},
	})
}

// AddCookie 添加新的Cookie
func AddCookie(c *gin.Context) {
	var req struct {
		ID     string `json:"id" binding:"required"`
		Cookie string `json:"cookie" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  "error",
			"message": err.Error(),
		})
		return
	}

	GlobalCookieManager.mu.Lock()
	defer GlobalCookieManager.mu.Unlock()

	// 检查ID是否已存在
	if _, exists := GlobalCookieManager.Cookies[req.ID]; exists {
		c.JSON(http.StatusConflict, gin.H{
			"status":  "error",
			"message": "Cookie ID already exists",
		})
		return
	}

	// 验证Cookie格式
	parts := SplitCookie(req.Cookie)
	hasBiliJct := false
	hasSessData := false

	for _, part := range parts {
		if part.Key == "bili_jct" {
			hasBiliJct = true
		}
		if part.Key == "SESSDATA" {
			hasSessData = true
		}
	}

	if !hasBiliJct || !hasSessData {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  "error",
			"message": "Cookie must contain bili_jct and SESSDATA",
		})
		return
	}

	// 添加新Cookie
	GlobalCookieManager.Cookies[req.ID] = req.Cookie

	c.JSON(http.StatusCreated, gin.H{
		"status":  "success",
		"message": "Cookie added successfully",
		"data":    gin.H{"id": req.ID},
	})
}

// UpdateCookieByID 更新指定ID的Cookie
func UpdateCookieByID(c *gin.Context) {
	cookieID := c.Param("cookieID")

	var req struct {
		Cookie string `json:"cookie" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  "error",
			"message": err.Error(),
		})
		return
	}

	GlobalCookieManager.mu.Lock()
	defer GlobalCookieManager.mu.Unlock()

	// 检查Cookie是否存在
	if _, exists := GlobalCookieManager.Cookies[cookieID]; !exists {
		c.JSON(http.StatusNotFound, gin.H{
			"status":  "error",
			"message": "Cookie not found",
		})
		return
	}

	// 验证Cookie格式
	parts := SplitCookie(req.Cookie)
	hasBiliJct := false
	hasSessData := false

	for _, part := range parts {
		if part.Key == "bili_jct" {
			hasBiliJct = true
		}
		if part.Key == "SESSDATA" {
			hasSessData = true
		}
	}

	if !hasBiliJct || !hasSessData {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  "error",
			"message": "Cookie must contain bili_jct and SESSDATA",
		})
		return
	}

	// 更新Cookie
	GlobalCookieManager.Cookies[cookieID] = req.Cookie

	c.JSON(http.StatusOK, gin.H{
		"status":  "success",
		"message": "Cookie updated successfully",
	})
}

// DeleteCookie 删除指定ID的Cookie
func DeleteCookie(c *gin.Context) {
	cookieID := c.Param("cookieID")

	GlobalCookieManager.mu.Lock()
	defer GlobalCookieManager.mu.Unlock()

	// 检查Cookie是否存在
	if _, exists := GlobalCookieManager.Cookies[cookieID]; !exists {
		c.JSON(http.StatusNotFound, gin.H{
			"status":  "error",
			"message": "Cookie not found",
		})
		return
	}

	// 删除Cookie
	delete(GlobalCookieManager.Cookies, cookieID)

	c.JSON(http.StatusOK, gin.H{
		"status":  "success",
		"message": "Cookie deleted successfully",
	})
}
