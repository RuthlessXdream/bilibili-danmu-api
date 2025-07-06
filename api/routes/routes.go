package routes

import (
	"net/http"

	"danmu_api/api/controllers"

	"github.com/gin-gonic/gin"
)

// SetupRoutes 设置所有API路由
func SetupRoutes(r *gin.Engine) {
	// 中间件配置
	r.Use(gin.Logger())
	r.Use(gin.Recovery())
	r.Use(corsMiddleware())

	// API路由组
	api := r.Group("/api")
	{
		// 健康检查
		api.GET("/health", func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{
				"status":  "success",
				"message": "Service is running",
			})
		})

		// Cookie管理
		cookies := api.Group("/cookies")
		{
			// 获取所有Cookie列表
			cookies.GET("", controllers.ListCookies)

			// 添加新Cookie
			cookies.POST("", controllers.AddCookie)

			// 获取指定Cookie
			cookies.GET("/:cookieID", controllers.GetCookie)

			// 更新指定Cookie
			cookies.PUT("/:cookieID", controllers.UpdateCookieByID)

			// 删除指定Cookie
			cookies.DELETE("/:cookieID", controllers.DeleteCookie)
		}

		// 保留原有默认Cookie管理（向后兼容）
		api.POST("/cookie/default", controllers.SetDefaultCookie)
		api.GET("/cookie/default", controllers.GetDefaultCookie)

		// 直播间管理
		rooms := api.Group("/rooms")
		{
			// 连接到直播间
			rooms.POST("/:roomID/connect", controllers.ConnectRoom)

			// 断开直播间连接
			rooms.POST("/:roomID/disconnect", controllers.DisconnectRoom)

			// 获取已连接的房间列表
			rooms.GET("/", controllers.ListRooms)

			// 获取房间信息
			rooms.GET("/:roomID/info", controllers.GetRoomInfo)

			// 发送弹幕
			rooms.POST("/:roomID/danmaku", controllers.SendDanmaku)

			// 更新Cookie
			rooms.POST("/:roomID/cookie", controllers.UpdateCookie)

			// WebSocket连接，用于接收实时弹幕
			rooms.GET("/:roomID/ws", controllers.WebSocketDanmaku)
		}
	}
}

// corsMiddleware 处理跨域请求的中间件
func corsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Origin, Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization")
		c.Writer.Header().Set("Access-Control-Expose-Headers", "Content-Length")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}
