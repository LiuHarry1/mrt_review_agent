#!/bin/bash

# Docker 镜像推送脚本
# 使用方法: ./scripts/push_image.sh [registry] [username] [tag]
# 示例: ./scripts/push_image.sh dockerhub myusername v1.0.0

set -e

REGISTRY=${1:-dockerhub}
USERNAME=${2:-}
TAG=${3:-latest}
IMAGE_NAME="mrt-review-backend"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}开始推送 Docker 镜像...${NC}"

# 检查是否已构建镜像
if ! docker images | grep -q "$IMAGE_NAME"; then
    echo -e "${YELLOW}镜像不存在，开始构建...${NC}"
    docker build -t $IMAGE_NAME:latest .
fi

case $REGISTRY in
    dockerhub|hub)
        if [ -z "$USERNAME" ]; then
            echo -e "${RED}错误: Docker Hub 需要提供用户名${NC}"
            echo "使用方法: $0 dockerhub <username> [tag]"
            exit 1
        fi
        REPO="docker.io/$USERNAME/$IMAGE_NAME"
        echo -e "${GREEN}使用 Docker Hub: $REPO${NC}"
        docker login docker.io
        docker tag $IMAGE_NAME:latest $REPO:$TAG
        docker push $REPO:$TAG
        echo -e "${GREEN}推送成功: $REPO:$TAG${NC}"
        ;;
    
    aliyun|ali)
        if [ -z "$USERNAME" ]; then
            echo -e "${RED}错误: 阿里云需要提供命名空间${NC}"
            echo "使用方法: $0 aliyun <namespace> [tag]"
            exit 1
        fi
        REGION=${4:-cn-hangzhou}
        REPO="registry.$REGION.aliyuncs.com/$USERNAME/$IMAGE_NAME"
        echo -e "${GREEN}使用阿里云容器镜像服务: $REPO${NC}"
        docker login --username=$USERNAME registry.$REGION.aliyuncs.com
        docker tag $IMAGE_NAME:latest $REPO:$TAG
        docker push $REPO:$TAG
        echo -e "${GREEN}推送成功: $REPO:$TAG${NC}"
        ;;
    
    tencent|tcr)
        if [ -z "$USERNAME" ]; then
            echo -e "${RED}错误: 腾讯云需要提供命名空间${NC}"
            echo "使用方法: $0 tencent <namespace> [tag]"
            exit 1
        fi
        REPO="ccr.ccs.tencentyun.com/$USERNAME/$IMAGE_NAME"
        echo -e "${GREEN}使用腾讯云容器镜像服务: $REPO${NC}"
        docker login ccr.ccs.tencentyun.com
        docker tag $IMAGE_NAME:latest $REPO:$TAG
        docker push $REPO:$TAG
        echo -e "${GREEN}推送成功: $REPO:$TAG${NC}"
        ;;
    
    github|ghcr)
        if [ -z "$USERNAME" ]; then
            echo -e "${RED}错误: GitHub 需要提供用户名${NC}"
            echo "使用方法: $0 github <username> [tag]"
            exit 1
        fi
        REPO="ghcr.io/$USERNAME/$IMAGE_NAME"
        echo -e "${GREEN}使用 GitHub Container Registry: $REPO${NC}"
        echo -e "${YELLOW}提示: 需要设置 GITHUB_TOKEN 环境变量或使用 docker login${NC}"
        if [ -z "$GITHUB_TOKEN" ]; then
            docker login ghcr.io -u $USERNAME
        else
            echo $GITHUB_TOKEN | docker login ghcr.io -u $USERNAME --password-stdin
        fi
        docker tag $IMAGE_NAME:latest $REPO:$TAG
        docker push $REPO:$TAG
        echo -e "${GREEN}推送成功: $REPO:$TAG${NC}"
        ;;
    
    *)
        echo -e "${RED}未知的仓库类型: $REGISTRY${NC}"
        echo "支持的仓库类型: dockerhub, aliyun, tencent, github"
        echo ""
        echo "使用方法:"
        echo "  $0 dockerhub <username> [tag]"
        echo "  $0 aliyun <namespace> [tag] [region]"
        echo "  $0 tencent <namespace> [tag]"
        echo "  $0 github <username> [tag]"
        exit 1
        ;;
esac

echo -e "${GREEN}完成!${NC}"

