#!/bin/bash

# B站直播弹幕API服务停止脚本

# 默认配置
PORT=3100
ALL_INSTANCES=false

# 显示帮助信息
show_help() {
    echo "B站直播弹幕API服务停止脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -p, --port PORT       指定要停止的API服务端口"
    echo "  -a, --all             停止所有danmu-api服务实例"
    echo "  -h, --help            显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 --port 3100        停止端口3100上的服务"
    echo "  $0 --all              停止所有danmu-api服务实例"
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
        -a|--all)
            ALL_INSTANCES=true
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

# 停止所有danmu-api实例
if [ "$ALL_INSTANCES" = true ]; then
    echo "正在停止所有B站直播弹幕API服务实例..."
    
    # 查找所有danmu-api进程
    PIDS=$(pgrep -f "danmu-api")
    
    if [ -z "$PIDS" ]; then
        echo "未找到任何运行中的danmu-api服务实例"
        exit 0
    fi
    
    echo "找到以下进程:"
    for PID in $PIDS; do
        CMD=$(ps -p $PID -o cmd=)
        echo "PID: $PID, 命令: $CMD"
    done
    
    read -p "确认停止这些进程? (y/n): " confirm
    if [[ $confirm != [yY] ]]; then
        echo "已取消操作"
        exit 0
    fi
    
    # 停止所有进程
    for PID in $PIDS; do
        kill $PID
        echo "已停止进程 $PID"
    done
    
    echo "所有danmu-api服务实例已停止"
    exit 0
fi

# 停止指定端口的服务
if [ -n "$PORT" ]; then
    echo "正在停止端口 $PORT 的B站直播弹幕API服务..."
    
    # 查找指定端口的进程
    PIDS=$(lsof -ti :$PORT)
    
    if [ -z "$PIDS" ]; then
        echo "未找到端口 $PORT 上运行的服务"
        exit 0
    fi
    
    echo "找到以下进程:"
    for PID in $PIDS; do
        CMD=$(ps -p $PID -o cmd=)
        echo "PID: $PID, 命令: $CMD"
    done
    
    read -p "确认停止这些进程? (y/n): " confirm
    if [[ $confirm != [yY] ]]; then
        echo "已取消操作"
        exit 0
    fi
    
    # 停止进程
    for PID in $PIDS; do
        kill $PID
    done
    
    echo "端口 $PORT 的服务已成功停止"
else
    echo "请指定要停止的服务端口或使用--all停止所有实例"
    show_help
    exit 1
fi 