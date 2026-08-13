.PHONY: help install dev test lint format clean build deploy db-init db-migrate db-upgrade logs shell celery-worker celery-beat

# 环境
ENV ?= development

# 颜色
BLUE := \033[36m
RESET := \033[0m

help:  ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)%-20s$(RESET) %s\n", $$1, $$2}'

install:  ## 安装所有依赖
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev:  ## 启动开发环境
	cd backend && docker-compose up -d db redis milvus
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	cd frontend && npm run dev

test:  ## 运行测试
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=term-missing

lint:  ## 代码检查
	cd backend && ruff check app/ tests/
	cd frontend && npx eslint src/

format:  ## 代码格式化
	cd backend && ruff format app/ tests/
	cd frontend && npx prettier --write src/

clean:  ## 清理缓存和临时文件
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov

build:  ## 构建 Docker 镜像
	docker-compose build

deploy:  ## 部署到服务器
	@echo "Deploying to $(ENV) environment..."
	docker-compose -f docker-compose.yml -f docker-compose.$(ENV).yml up -d

db-init:  ## 初始化数据库
	cd backend && python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"

db-migrate:  ## 创建数据库迁移
	cd backend && alembic revision --autogenerate -m "$(msg)"

db-upgrade:  ## 升级数据库
	cd backend && alembic upgrade head

logs:  ## 查看日志
	tail -f backend/logs/app.log

shell:  ## 进入 Python shell
	cd backend && python

celery-worker:  ## 启动 Celery Worker
	cd backend && celery -A app.tasks.celery_app worker -l info -Q agent,cleanup

celery-beat:  ## 启动 Celery Beat
	cd backend && celery -A app.tasks.celery_app beat -l info