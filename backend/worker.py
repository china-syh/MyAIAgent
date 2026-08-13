"""
AI 漫剧 Agent - 后台生成任务 Worker
=====================================
每隔 10 分钟轮询后端 API，获取待处理的图像生成 (image_gen) 和视频合成 (video_compose) 任务。
实际 AI 生成由 AI 助手完成，worker 负责：
  1. 轮询并将待处理任务写入队列
  2. 检测 AI 助手生成的完成文件
  3. 提交结果到后端 API

流程:
  1. 轮询 GET /api/v1/tasks/pending/generation
  2. 写入 generated/queue/pending/{task_id}.json  (等待 AI 助手处理)
  3. AI 助手使用 GenerateImage/GenerateVideo 生成内容
  4. 生成完成后，写入 generated/queue/ready/{task_id}.json
  5. Worker 检测到 ready 文件后，调用 POST /api/v1/tasks/{task_id}/submit-generation
  6. 提交成功后删除 ready 文件

用法:
  python worker.py                    # 单次运行
  python worker.py --loop             # 持续轮询 (每 10 分钟)
  python worker.py --loop --interval 5  # 自定义间隔 (分钟)

运行依赖:
  pip install httpx
"""

import argparse
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    import httpx
except ImportError:
    print("请先安装 httpx: pip install httpx")
    sys.exit(1)

# ── 路径配置 ─────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
GENERATED_DIR = BASE_DIR / "generated"
QUEUE_DIR = GENERATED_DIR / "queue"
PENDING_DIR = QUEUE_DIR / "pending"
READY_DIR = QUEUE_DIR / "ready"
IMAGES_DIR = GENERATED_DIR / "images"
VIDEOS_DIR = GENERATED_DIR / "videos"
API_BASE = "http://localhost:8000/api/v1"

# ── 日志配置 ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("worker")


# ── 工具函数 ─────────────────────────────────────────────────
def ensure_dirs():
    """确保所有需要的目录存在"""
    for d in [GENERATED_DIR, QUEUE_DIR, PENDING_DIR, READY_DIR, IMAGES_DIR, VIDEOS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    logger.info("✅ 目录检查完成")


def fetch_pending_tasks(client: httpx.Client) -> list:
    """获取所有待处理的 image_gen 和 video_compose 任务"""
    try:
        resp = client.get(f"{API_BASE}/tasks/pending/generation", timeout=10)
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") == 0:
            tasks = body.get("data", [])
            logger.info(f"📥 获取到 {len(tasks)} 个待处理任务")
            return tasks
        else:
            logger.warning(f"⚠️ API 返回异常: {body}")
            return []
    except httpx.ConnectError:
        logger.warning("⚠️ 后端未连接 (http://localhost:8000)")
        return []
    except Exception as e:
        logger.error(f"❌ 获取任务失败: {e}")
        return []


def write_pending_task(task: dict):
    """将待处理任务写入队列"""
    task_id = task.get("id", str(uuid.uuid4()))
    filepath = PENDING_DIR / f"{task_id}.json"
    if filepath.exists():
        return  # 已存在，跳过
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(task, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"  ✍️ 写入队列: {task_id} ({task.get('type')})")


def scan_ready_tasks() -> list:
    """扫描 ready 目录，获取已完成的任务"""
    ready_files = []
    for f in sorted(READY_DIR.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            ready_files.append((f, data))
        except Exception as e:
            logger.warning(f"  ⚠️ 读取就绪文件失败 {f.name}: {e}")
    return ready_files


def submit_generation_result(client: httpx.Client, task_id: str, result: dict) -> bool:
    """提交生成结果到后端 API"""
    try:
        resp = client.post(
            f"{API_BASE}/tasks/{task_id}/submit-generation",
            json={"result": result},
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") == 0:
            logger.info(f"  ✅ 提交成功: {task_id}")
            return True
        else:
            logger.warning(f"  ⚠️ 提交返回异常: {task_id} -> {body}")
            return False
    except Exception as e:
        logger.error(f"  ❌ 提交失败: {task_id} -> {e}")
        return False


def process_ready_tasks(client: httpx.Client):
    """处理所有已就绪的任务"""
    ready_items = scan_ready_tasks()
    if not ready_items:
        return

    logger.info(f"📤 发现 {len(ready_items)} 个已完成任务，提交中...")
    for filepath, data in ready_items:
        task_id = data.get("task_id", filepath.stem)
        result = data.get("result", {})
        success = submit_generation_result(client, task_id, result)
        if success:
            try:
                filepath.unlink()
            except FileNotFoundError:
                pass
            logger.info(f"  🗑️ 已清理就绪文件: {filepath.name}")


def run_once(client: httpx.Client):
    """单次轮询处理"""
    # 1. 先提交已完成的
    process_ready_tasks(client)

    # 2. 获取待处理任务
    tasks = fetch_pending_tasks(client)
    if not tasks:
        return

    # 3. 写入队列
    for task in tasks:
        task_id = task.get("id")
        task_type = task.get("type")
        task_result = task.get("result", {})
        prompt = task_result.get("prompt", "")
        storyboard_id = task_result.get("storyboard_id", "")
        episode_id = task_result.get("episode_id", "")

        logger.info(f"  📋 待处理任务: {task_id}")
        logger.info(f"     类型: {task_type}")
        if prompt:
            logger.info(f"     提示词: {prompt[:80]}...")
        if storyboard_id:
            logger.info(f"     分镜ID: {storyboard_id}")
        if episode_id:
            logger.info(f"     剧集ID: {episode_id}")

        # 写入队列
        write_pending_task(task)

    # 输出提示信息
    logger.info("")
    logger.info("=" * 60)
    logger.info("📢 待处理任务已写入队列，请使用 AI 生成工具处理:")
    logger.info("")
    logger.info("  image_gen 任务 → 使用 GenerateImage 工具 (Seedream)")
    logger.info("  video_compose 任务 → 使用 GenerateVideo 工具 (Seedance)")
    logger.info("")
    logger.info("  生成完成后，将结果写入 generated/queue/ready/{task_id}.json")
    logger.info("  Worker 会自动检测并提交到后端")
    logger.info("=" * 60)


def run_loop(interval_minutes: int = 10):
    """持续轮询模式"""
    logger.info(f"🔄 启动后台 Worker (轮询间隔: {interval_minutes} 分钟)")
    logger.info(f"   API 地址: {API_BASE}")
    logger.info(f"   队列目录: {QUEUE_DIR}")
    logger.info("")

    with httpx.Client() as client:
        while True:
            try:
                now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                logger.info(f"── [{now}] 开始轮询 ──")
                run_once(client)
            except KeyboardInterrupt:
                logger.info("👋 Worker 已停止")
                break
            except Exception as e:
                logger.error(f"❌ 轮询异常: {e}")

            logger.info(f"⏳ 等待 {interval_minutes} 分钟后下一轮...")
            logger.info("")
            time.sleep(interval_minutes * 60)


# ── 主入口 ───────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AI 漫剧 Agent - 后台生成任务 Worker")
    parser.add_argument("--loop", action="store_true", help="持续轮询模式")
    parser.add_argument("--interval", "-i", type=int, default=10, help="轮询间隔 (分钟)")
    args = parser.parse_args()

    ensure_dirs()

    if args.loop:
        run_loop(args.interval)
    else:
        with httpx.Client() as client:
            run_once(client)


if __name__ == "__main__":
    main()