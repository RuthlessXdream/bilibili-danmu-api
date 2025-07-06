package main

import (
	"danmu_api/api/routes"
	"flag"
	"net/http"
	"os"
	"time"

	"github.com/gin-gonic/gin"
	log "github.com/sirupsen/logrus"
)

func main() {
	// 解析命令行参数
	port := flag.String("port", "8080", "API服务端口")
	logLevel := flag.String("log-level", "info", "日志级别 (debug, info, warn, error)")
	flag.Parse()

	// 配置日志
	setupLogger(*logLevel)

	// 设置Gin模式
	gin.SetMode(getGinMode())

	// 创建路由
	r := gin.Default()

	// 配置路由
	routes.SetupRoutes(r)

	// 启动服务器
	srv := &http.Server{
		Addr:         ":" + *port,
		Handler:      r,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	log.Infof("B站直播弹幕API服务已启动，监听端口: %s", *port)
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("服务器启动失败: %s", err)
	}
}

// 设置日志配置
func setupLogger(level string) {
	// 设置日志格式
	log.SetFormatter(&log.TextFormatter{
		FullTimestamp:   true,
		TimestampFormat: "2006-01-02 15:04:05",
	})

	// 设置日志输出
	log.SetOutput(os.Stdout)

	// 设置日志级别
	switch level {
	case "debug":
		log.SetLevel(log.DebugLevel)
	case "info":
		log.SetLevel(log.InfoLevel)
	case "warn":
		log.SetLevel(log.WarnLevel)
	case "error":
		log.SetLevel(log.ErrorLevel)
	default:
		log.SetLevel(log.InfoLevel)
	}
}

// 获取Gin运行模式
func getGinMode() string {
	env := os.Getenv("GIN_MODE")
	if env == "" {
		return gin.ReleaseMode // 默认使用生产模式
	}
	return env
}
