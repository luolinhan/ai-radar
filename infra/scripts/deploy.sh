#!/bin/bash
# AI Radar 部署脚本

set -e

echo "=== AI Radar 部署脚本 ==="

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装"
    exit 1
fi

# 检查Docker Compose
if ! command -v docker compose &> /dev/null; then
    echo "错误: Docker Compose未安装"
    exit 1
fi

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "警告: .env文件不存在，使用.env.example"
    cp .env.example .env
fi

# 进入仓库根目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/../.."

# 停止旧容器
echo "停止旧容器..."
docker compose down || true

# 构建镜像
echo "构建镜像..."
docker compose build

# 启动服务
echo "启动服务..."
docker compose up -d

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo "检查服务状态..."
docker compose ps

# 健康检查
echo "API健康检查..."
curl -s http://localhost:8000/health || echo "API未就绪"

echo ""
echo "=== 部署完成 ==="
echo "API: http://localhost:8000"
echo "控制台: http://localhost:3000"
echo ""
echo "查看日志: docker compose logs -f"
