#!/bin/bash
# AI 漫剧 Agent - 一键启动脚本

set -e

echo "🚀 AI 漫剧 Agent 启动中..."
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 请先安装 Docker"
    exit 1
fi

# 检查 Docker Compose
if ! command -v docker compose &> /dev/null; then
    echo "❌ 请先安装 Docker Compose"
    exit 1
fi

# 启动基础设施
echo "📦 启动基础设施 (PostgreSQL + Milvus + Redis)..."
cd backend
docker compose up -d postgres milvus redis
echo "⏳ 等待数据库就绪..."
sleep 10

# 启动后端
echo "🔧 启动后端服务..."
docker compose up -d backend
echo "⏳ 等待后端就绪..."
sleep 5

# 启动前端
echo "🎨 启动前端..."
docker compose up -d frontend

echo ""
echo "✅ AI 漫剧 Agent 启动完成!"
echo "   📋 前端: http://localhost"
echo "   🔧 后端: http://localhost:8000"
echo "   📚 API 文档: http://localhost:8000/docs"
echo "   🗄️  PostgreSQL: localhost:5432"
echo "   🔍 Milvus: localhost:19530"
echo "   ⚡ Redis: localhost:6379"