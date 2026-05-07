#!/bin/bash
# AI文物情感交互系统DNA - 安装脚本
# 版本: v1.2
# 架构师: 元宝

set -e  # 遇到错误退出

echo "🧬 AI文物情感交互系统DNA安装脚本"
echo "=================================="

# 检查Python版本
echo "🔍 检查系统环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装，请先安装Python3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Python版本: $PYTHON_VERSION"

# 检查PIP
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3未安装，请先安装pip3"
    exit 1
fi

# 创建目录结构
echo "📁 创建目录结构..."
mkdir -p dna_core
mkdir -p dna_expression
mkdir -p dna_apis
mkdir -p dna_apis/endpoints
mkdir -p dna_apis/models
mkdir -p dna_frontend/src
mkdir -p dna_frontend/src/components
mkdir -p dna_frontend/src/stores
mkdir -p dna_frontend/src/websocket
mkdir -p dna_frontend/src/styles
mkdir -p dna_monitor
mkdir -p dna_ops/scripts
mkdir -p dna_ops/docker
mkdir -p dna_ops/kubernetes
mkdir -p dna_logs
mkdir -p dna_patches/patches
mkdir -p dna_tests
mkdir -p dna_ui
mkdir -p dna_docs
mkdir -p config

echo "✅ 目录结构创建完成"

# 安装Python依赖
echo "📦 安装Python依赖..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    echo "✅ Python依赖安装完成"
else
    echo "⚠️ requirements.txt未找到，跳过Python依赖安装"
fi

# 安装Node.js依赖
echo "📦 安装Node.js依赖..."
if [ -f "package.json" ]; then
    if command -v npm &> /dev/null; then
        npm install
        echo "✅ Node.js依赖安装完成"
    else
        echo "⚠️ npm未安装，跳过前端依赖安装"
    fi
else
    echo "⚠️ package.json未找到，跳过前端依赖安装"
fi

# 检查Docker
echo "🐳 检查Docker环境..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "✅ Docker版本: $DOCKER_VERSION"
    
    if command -v docker-compose &> /dev/null; then
        echo "✅ Docker Compose可用"
    else
        echo "⚠️ Docker Compose不可用，请安装"
    fi
else
    echo "⚠️ Docker未安装，容器化功能将不可用"
fi

# 检查CUDA
echo "🎮 检查GPU支持..."
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU检测到"
    NVIDIA_DRIVER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
    echo "✅ NVIDIA驱动版本: $NVIDIA_DRIVER"
else
    echo "⚠️ 未检测到NVIDIA GPU，将使用CPU模式"
fi

# 下载预训练模型（可选）
echo "⬇️ 下载预训练模型（可选）..."
read -p "是否下载预训练模型？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "正在下载模型，这可能需要一些时间..."
    
    # 创建模型目录
    mkdir -p models
    
    # 下载嵌入模型
    echo "下载嵌入模型..."
    python3 -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-large-zh-v1.5')
print('✅ 嵌入模型下载完成')
    " || echo "⚠️ 嵌入模型下载失败"
fi

# 设置环境变量
echo "🔧 设置环境变量..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ 环境变量模板已创建，请编辑 .env 文件"
else
    echo "✅ .env文件已存在"
fi

# 初始化数据库
echo "🗃️ 初始化数据库..."
if command -v docker &> /dev/null; then
    echo "启动向量数据库服务..."
    docker-compose -f dna_ops/docker/docker-compose.yml up -d qdrant
    sleep 5
    echo "✅ 向量数据库已启动"
else
    echo "⚠️ Docker未安装，跳过数据库初始化"
fi

# 运行健康检查
echo "🏥 运行系统健康检查..."
python3 dna_monitor/health_monitor.py --check-all

echo ""
echo "🎉 AI文物情感交互系统DNA安装完成！"
echo ""
echo "下一步："
echo "1. 编辑 .env 文件配置环境变量"
echo "2. 运行: ./dna_ops/scripts/start.sh 启动系统"
echo "3. 访问: http://localhost:8000/docs 查看API文档"
echo "4. 访问: http://localhost:3000 使用前端界面"
echo ""
echo "🧬 DNA编码: OPEN_SOURCE_MUSEUM_AI_V1.2"
echo "📅 激活时间: $(date)"