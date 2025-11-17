#!/bin/bash

# 手动拉取基础镜像脚本（带重试和代理支持）

set -e

IMAGE="python:3.11-slim"
MAX_RETRIES=5
RETRY_DELAY=5

echo "尝试拉取基础镜像: $IMAGE"
echo ""

# 检查是否设置了代理
if [ -n "$HTTP_PROXY" ] || [ -n "$HTTPS_PROXY" ]; then
    echo "检测到代理设置:"
    [ -n "$HTTP_PROXY" ] && echo "  HTTP_PROXY=$HTTP_PROXY"
    [ -n "$HTTPS_PROXY" ] && echo "  HTTPS_PROXY=$HTTPS_PROXY"
    echo ""
fi

# 尝试拉取镜像（带重试）
for i in $(seq 1 $MAX_RETRIES); do
    echo "尝试 $i/$MAX_RETRIES..."
    
    if docker pull $IMAGE; then
        echo ""
        echo "✅ 成功拉取镜像: $IMAGE"
        echo ""
        echo "现在可以构建应用镜像："
        echo "  docker build -t mrt-review-backend:latest ."
        exit 0
    else
        if [ $i -lt $MAX_RETRIES ]; then
            echo "❌ 拉取失败，等待 ${RETRY_DELAY} 秒后重试..."
            sleep $RETRY_DELAY
        else
            echo ""
            echo "❌ 所有重试都失败了"
            echo ""
            echo "建议："
            echo "1. 配置 Docker 镜像加速器（运行: ./fix_docker_network.sh）"
            echo "2. 使用代理（设置 HTTP_PROXY 和 HTTPS_PROXY 环境变量）"
            echo "3. 检查网络连接"
            exit 1
        fi
    fi
done

