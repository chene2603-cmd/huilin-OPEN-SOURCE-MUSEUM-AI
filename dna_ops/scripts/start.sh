#!/bin/bash
# AI文物情感交互系统DNA - 启动脚本
# 版本: v1.2

set -e

echo "🚀 启动AI文物情感交互系统DNA..."
echo "=================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查环境变量
check_env() {
    log_info "检查环境变量..."
    
    if [ ! -f ".env" ]; then
        log_warning ".env文件不存在，使用默认配置"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_info "已创建.env文件，请根据需要修改"
        fi
    fi
    
    # 加载环境变量
    set -a
    source .env
    set +a
    
    log_success "环境变量检查完成"
}

# 检查依赖服务
check_dependencies() {
    log_info "检查依赖服务..."
    
    # 检查向量数据库
    if [ "$USE_VECTOR_DB" = "true" ]; then
        if docker ps | grep -q "qdrant"; then
            log_success "向量数据库运行中"
        else
            log_warning "向量数据库未运行，正在启动..."
            docker-compose -f dna_ops/docker/docker-compose.yml up -d qdrant
            sleep 3
        fi
    fi
    
    # 检查Redis
    if [ "$USE_REDIS" = "true" ]; then
        if docker ps | grep -q "redis"; then
            log_success "Redis运行中"
        else
            log_warning "Redis未运行，正在启动..."
            docker-compose -f dna_ops/docker/docker-compose.yml up -d redis
            sleep 2
        fi
    fi
    
    log_success "依赖服务检查完成"
}

# 启动API服务器
start_api() {
    log_info "启动DNA API服务器..."
    
    # 检查端口是否被占用
    if lsof -Pi :${API_PORT:-8000} -sTCP:LISTEN -t >/dev/null ; then
        log_warning "端口${API_PORT:-8000}已被占用，尝试停止现有进程..."
        kill -9 $(lsof -ti:${API_PORT:-8000}) 2>/dev/null || true
        sleep 1
    fi
    
    # 启动API服务器
    cd dna_apis
    nohup python3 -m uvicorn main:app \
        --host ${API_HOST:-0.0.0.0} \
        --port ${API_PORT:-8000} \
        --reload \
        --log-level info \
        > ../dna_logs/api_server.log 2>&1 &
    
    API_PID=$!
    echo $API_PID > ../dna_logs/api.pid
    
    # 等待API启动
    sleep 5
    
    # 检查API是否启动成功
    if curl -s http://localhost:${API_PORT:-8000}/health > /dev/null; then
        log_success "DNA API服务器启动成功 (PID: $API_PID)"
        log_info "API文档: http://localhost:${API_PORT:-8000}/docs"
    else
        log_error "DNA API服务器启动失败"
        tail -20 ../dna_logs/api_server.log
        exit 1
    fi
    
    cd ..
}

# 启动前端服务器
start_frontend() {
    if [ "$START_FRONTEND" = "false" ]; then
        log_info "跳过前端启动"
        return
    fi
    
    log_info "启动DNA前端服务器..."
    
    # 检查端口是否被占用
    if lsof -Pi :${FRONTEND_PORT:-3000} -sTCP:LISTEN -t >/dev/null ; then
        log_warning "端口${FRONTEND_PORT:-3000}已被占用，尝试停止现有进程..."
        kill -9 $(lsof -ti:${FRONTEND_PORT:-3000}) 2>/dev/null || true
        sleep 1
    fi
    
    # 启动前端服务器
    cd dna_frontend
    
    if [ -f "package.json" ]; then
        # 检查node_modules
        if [ ! -d "node_modules" ]; then
            log_warning "node_modules不存在，正在安装依赖..."
            npm install
        fi
        
        # 启动开发服务器
        if command -v npm &> /dev/null; then
            nohup npm run dev > ../dna_logs/frontend.log 2>&1 &
            FRONTEND_PID=$!
            echo $FRONTEND_PID > ../dna_logs/frontend.pid
            
            sleep 3
            
            # 检查前端是否启动成功
            if curl -s http://localhost:${FRONTEND_PORT:-3000} > /dev/null; then
                log_success "DNA前端服务器启动成功 (PID: $FRONTEND_PID)"
                log_info "前端地址: http://localhost:${FRONTEND_PORT:-3000}"
            else
                log_warning "DNA前端服务器可能启动失败，请检查日志"
            fi
        else
            log_warning "npm未安装，跳过前端启动"
        fi
    else
        log_warning "前端项目不存在，跳过前端启动"
    fi
    
    cd ..
}

# 启动监控服务
start_monitor() {
    log_info "启动DNA健康监控..."
    
    cd dna_monitor
    nohup python3 health_monitor.py \
        --interval ${MONITOR_INTERVAL:-60} \
        --log-file ../dna_logs/monitor.log \
        > ../dna_logs/monitor.log 2>&1 &
    
    MONITOR_PID=$!
    echo $MONITOR_PID > ../dna_logs/monitor.pid
    
    log_success "DNA健康监控启动成功 (PID: $MONITOR_PID)"
    cd ..
}

# 显示启动信息
show_startup_info() {
    echo ""
    echo "=" * 50
    echo "🧬 AI文物情感交互系统DNA v1.2"
    echo "=" * 50
    echo ""
    echo "✅ 系统启动完成！"
    echo ""
    echo "🌐 服务地址:"
    echo "   API文档:      http://localhost:${API_PORT:-8000}/docs"
    echo "   前端界面:     http://localhost:${FRONTEND_PORT:-3000}"
    echo "   健康检查:     http://localhost:${API_PORT:-8000}/health"
    echo "   监控面板:     http://localhost:${API_PORT:-8000}/monitor"
    echo ""
    echo "📊 监控日志:"
    echo "   API日志:      dna_logs/api_server.log"
    echo "   前端日志:     dna_logs/frontend.log"
    echo "   监控日志:     dna_logs/monitor.log"
    echo ""
    echo "🔧 管理命令:"
    echo "   停止系统:     ./dna_ops/scripts/stop.sh"
    echo "   重启系统:     ./dna_ops/scripts/restart.sh"
    echo "   查看状态:     ./dna_ops/scripts/status.sh"
    echo ""
    echo "🧬 DNA编码: OPEN_SOURCE_MUSEUM_AI_V1.2"
    echo "📅 启动时间: $(date)"
    echo ""
    echo "🎉 开始与文物对话吧！"
    echo "=" * 50
}

# 主启动流程
main() {
    echo ""
    echo "🧬 AI文物情感交互系统DNA启动流程"
    echo "=================================="
    
    # 检查环境
    check_env
    
    # 检查依赖
    check_dependencies
    
    # 启动服务
    start_api
    start_frontend
    start_monitor
    
    # 显示启动信息
    show_startup_info
    
    # 保存启动配置
    echo "API_PID=$API_PID" > .dna_runtime
    echo "FRONTEND_PID=$FRONTEND_PID" >> .dna_runtime
    echo "MONITOR_PID=$MONITOR_PID" >> .dna_runtime
    echo "START_TIME=$(date +%s)" >> .dna_runtime
}

# 优雅停止函数
cleanup() {
    echo ""
    log_info "正在停止DNA系统..."
    
    # 停止监控
    if [ -f "dna_logs/monitor.pid" ]; then
        MONITOR_PID=$(cat dna_logs/monitor.pid)
        kill $MONITOR_PID 2>/dev/null || true
        rm dna_logs/monitor.pid
    fi
    
    # 停止前端
    if [ -f "dna_logs/frontend.pid" ]; then
        FRONTEND_PID=$(cat dna_logs/frontend.pid)
        kill $FRONTEND_PID 2>/dev/null || true
        rm dna_logs/frontend.pid
    fi
    
    # 停止API
    if [ -f "dna_logs/api.pid" ]; then
        API_PID=$(cat dna_logs/api.pid)
        kill $API_PID 2>/dev/null || true
        rm dna_logs/api.pid
    fi
    
    log_success "DNA系统已停止"
    exit 0
}

# 注册退出处理
trap cleanup SIGINT SIGTERM EXIT

# 运行主函数
main "$@"

# 保持脚本运行
log_info "DNA系统运行中，按Ctrl+C停止..."
while true; do
    sleep 1
done