#!/bin/bash

# B站直播弹幕API服务启动脚本

# 默认配置
PORT=3100
LOG_LEVEL="info"
LOG_FILE="api.log"
AUTO_BUILD=false
AUTO_INSTALL_DEPS=false

# 显示帮助信息
show_help() {
    echo "B站直播弹幕API服务启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -p, --port PORT       指定API服务端口 (默认: 3100)"
    echo "  -l, --log-level LEVEL 指定日志级别 [debug|info|warn|error] (默认: info)"
    echo "  -f, --log-file FILE   指定日志文件 (默认: api.log)"
    echo "  -b, --build           自动编译程序 (如果可执行文件不存在或过期)"
    echo "  -d, --deps            自动安装依赖 (如果缺少依赖)"
    echo "  -h, --help            显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 --port 9000 --log-level debug"
    echo "  $0 -p 8080 -l warn -f my_api.log"
    echo "  $0 --build --deps     自动安装依赖并编译程序"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -p|--port)
            PORT="$2"
            shift
            shift
            ;;
        -l|--log-level)
            LOG_LEVEL="$2"
            shift
            shift
            ;;
        -f|--log-file)
            LOG_FILE="$2"
            shift
            shift
            ;;
        -b|--build)
            AUTO_BUILD=true
            shift
            ;;
        -d|--deps)
            AUTO_INSTALL_DEPS=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查Go环境
check_go_env() {
    if ! command -v go &> /dev/null; then
        echo "错误: 未安装Go环境"
        echo "请先安装Go: https://golang.org/doc/install"
        exit 1
    fi

    GO_VERSION=$(go version | awk '{print $3}' | sed 's/go//')
    MAJOR_VERSION=$(echo $GO_VERSION | cut -d. -f1)
    MINOR_VERSION=$(echo $GO_VERSION | cut -d. -f2)

    if [[ $MAJOR_VERSION -lt 1 || ($MAJOR_VERSION -eq 1 && $MINOR_VERSION -lt 16) ]]; then
        echo "警告: Go版本过低 ($GO_VERSION), 建议使用Go 1.16+"
        read -p "是否继续? (y/n): " confirm
        if [[ $confirm != [yY] ]]; then
            exit 0
        fi
    else
        echo "✓ Go环境检查通过 (版本 $GO_VERSION)"
    fi
}

# 安装依赖
install_dependencies() {
    echo "正在安装/更新依赖..."
    go mod tidy
    if [ $? -ne 0 ]; then
        echo "错误: 依赖安装失败"
        exit 1
    fi
    echo "✓ 依赖安装成功"
}

# 编译程序
build_program() {
    echo "正在编译程序..."
    go build -o danmu-api
    if [ $? -ne 0 ]; then
        echo "错误: 编译失败"
        exit 1
    fi
    echo "✓ 编译成功"
}

# 检查可执行文件是否需要重新编译
check_executable() {
    if [ ! -f "./danmu-api" ]; then
        echo "未找到可执行文件 danmu-api"
        if [ "$AUTO_BUILD" = true ]; then
            build_program
        else
            echo "请先运行 'go build -o danmu-api' 编译程序，或使用 --build 选项自动编译"
            exit 1
        fi
    elif [ "$AUTO_BUILD" = true ]; then
        # 检查源文件是否比可执行文件新
        NEWEST_GO_FILE=$(find . -name "*.go" -type f -newer danmu-api 2>/dev/null | head -1)
        if [ -n "$NEWEST_GO_FILE" ]; then
            echo "检测到源文件变更，需要重新编译"
            build_program
        else
            echo "✓ 可执行文件已是最新"
        fi
    else
        echo "✓ 可执行文件检查通过"
    fi
}

# 主流程
echo "===== B站直播弹幕API服务启动 ====="

# 检查环境
check_go_env

# 安装依赖（如果需要）
if [ "$AUTO_INSTALL_DEPS" = true ]; then
    install_dependencies
fi

# 检查可执行文件
check_executable

# 检查端口是否被占用
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "错误: 端口 $PORT 已被占用"
    exit 1
fi

# 检查是否已有相同服务运行
if pgrep -f "danmu-api.*--port $PORT" > /dev/null; then
    echo "警告: 已有相同服务在运行"
    read -p "是否继续启动新服务? (y/n): " confirm
    if [[ $confirm != [yY] ]]; then
        echo "已取消启动"
        exit 0
    fi
fi

# 启动服务
echo "正在启动B站直播弹幕API服务..."
echo "端口: $PORT"
echo "日志级别: $LOG_LEVEL"
echo "日志文件: $LOG_FILE"

nohup ./danmu-api --port $PORT --log-level $LOG_LEVEL > $LOG_FILE 2>&1 &

# 检查服务是否成功启动
PID=$!
sleep 1
if ps -p $PID > /dev/null; then
    echo "服务已成功启动，PID: $PID"
    echo "API文档: http://localhost:$PORT/api/health"
    echo "WebSocket测试页面: file://$(pwd)/ws_test.html"
    echo "可以通过 'tail -f $LOG_FILE' 查看日志"
else
    echo "服务启动失败，请检查日志文件 $LOG_FILE"
fi 