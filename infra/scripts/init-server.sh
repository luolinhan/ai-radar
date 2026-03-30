#!/bin/bash
# AI Radar 服务器初始化脚本

set -e

echo "=== AI Radar 服务器初始化 ==="

# 创建项目目录
mkdir -p /root/ai-radar

# 检查Docker
if command -v docker &> /dev/null; then
    echo "Docker已安装: $(docker --version)"
else
    echo "安装Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# 检查Docker Compose
if command -v docker compose &> /dev/null; then
    echo "Docker Compose已安装"
else
    echo "安装Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

echo "=== 初始化完成 ==="
echo "请将项目代码上传到 /root/ai-radar"