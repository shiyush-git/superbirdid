#!/bin/bash
# 构建并运行SuperBirdID Docker镜像脚本（适配Mac mini/Apple Silicon）
# 用法：bash build_and_run_docker.sh

set -e

IMAGE_NAME=superbirdid:latest
CONTAINER_NAME=superbirdid_api
HOST_PORT=5156
DATA_DIR=/Volumes/External/Immich-Library/library/admin  # 挂载本地离线数据目录，如需更改请修改此行

# 检查docker命令
if ! command -v docker >/dev/null 2>&1; then
  echo "❌ 未检测到docker命令，请先安装 Docker Desktop for Mac (arm64) 并确保已启动。"
  exit 127
fi

# 检查平台
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" || "$ARCH" == "aarch64" ]]; then
  echo "✓ 检测到Apple Silicon (arm64) 架构，自动适配多平台镜像构建。"
else
  echo "⚠️ 当前非arm64架构，若为Intel Mac请确保镜像基础镜像兼容。"
fi

# 检查数据目录和模型目录是否存在
if [ ! -d "$DATA_DIR" ]; then
    echo "❌ 数据目录 $DATA_DIR 不存在，请检查配置"
    exit 1
fi

YOLO_MODELS_DIR=$(pwd)/yolo_models  # 挂载本地yolo模型目录，如需更改请修改此行
if [ ! -d "$YOLO_MODELS_DIR" ]; then
    echo "❌ YOLO模型目录 $YOLO_MODELS_DIR 不存在"
    exit 1
fi

echo "[1/3] 构建Docker镜像..."
docker build --platform linux/arm64 -t $IMAGE_NAME .

echo "[2/3] 停止并移除旧容器（如有）..."
docker rm -f $CONTAINER_NAME 2>/dev/null || true

echo "[3/3] 启动新容器..."
YOLO_MODELS_DIR=$(pwd)/yolo_models  # 挂载本地yolo模型目录，如需更改请修改此行
docker run -d \
  --name $CONTAINER_NAME \
  -p $HOST_PORT:5156 \
  -v $DATA_DIR:/photo \
  -v $YOLO_MODELS_DIR:/app/yolo_models \
  $IMAGE_NAME

echo "✓ SuperBirdID API 已启动: http://localhost:$HOST_PORT/health"
