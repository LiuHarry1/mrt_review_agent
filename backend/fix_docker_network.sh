#!/bin/bash

# Docker 网络问题修复脚本
# 用于配置 Docker 镜像加速器

set -e

echo "=========================================="
echo "Docker 镜像加速器配置助手"
echo "=========================================="
echo ""

# 检测操作系统
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "检测到 macOS 系统"
    echo ""
    echo "请按照以下步骤手动配置："
    echo ""
    echo "1. 打开 Docker Desktop"
    echo "2. 点击右上角设置图标（齿轮）"
    echo "3. 选择 'Docker Engine'"
    echo "4. 在 JSON 配置中添加以下内容："
    echo ""
    cat << 'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com",
    "https://dockerhub.azk8s.cn"
  ]
}
EOF
    echo ""
    echo "5. 点击 'Apply & Restart'"
    echo "6. 等待 Docker 重启完成"
    echo ""
    echo "配置完成后，运行以下命令验证："
    echo "  docker info | grep -A 5 'Registry Mirrors'"
    echo ""
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "检测到 Linux 系统"
    echo ""
    
    DOCKER_DAEMON_JSON="/etc/docker/daemon.json"
    
    # 检查是否有写权限
    if [ ! -w "$DOCKER_DAEMON_JSON" ] && [ ! -w "$(dirname $DOCKER_DAEMON_JSON)" ]; then
        echo "需要 sudo 权限来修改 Docker 配置"
        SUDO_CMD="sudo"
    else
        SUDO_CMD=""
    fi
    
    # 备份现有配置
    if [ -f "$DOCKER_DAEMON_JSON" ]; then
        echo "备份现有配置到 ${DOCKER_DAEMON_JSON}.bak"
        $SUDO_CMD cp "$DOCKER_DAEMON_JSON" "${DOCKER_DAEMON_JSON}.bak"
    fi
    
    # 创建或更新配置
    echo "配置 Docker 镜像加速器..."
    $SUDO_CMD tee "$DOCKER_DAEMON_JSON" > /dev/null << 'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com",
    "https://dockerhub.azk8s.cn"
  ]
}
EOF
    
    echo "配置完成！"
    echo ""
    echo "重启 Docker 服务..."
    $SUDO_CMD systemctl daemon-reload
    $SUDO_CMD systemctl restart docker
    
    echo ""
    echo "验证配置："
    docker info | grep -A 5 "Registry Mirrors" || echo "请检查 Docker 是否正常运行"
    
else
    echo "未识别的操作系统: $OSTYPE"
    echo "请手动配置 Docker 镜像加速器"
    exit 1
fi

echo ""
echo "=========================================="
echo "配置完成！现在可以尝试："
echo "  docker pull python:3.11-slim"
echo "  docker build -t mrt-review-backend:latest ."
echo "=========================================="

