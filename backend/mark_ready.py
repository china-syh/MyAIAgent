"""
标记任务为已就绪 — 供 AI 助手在生成完成后调用
=============================================
用法:
  # 标记 image_gen 任务完成
  python mark_ready.py <task_id> --image-url /generated/images/<task_id>.png --storyboard-id <storyboard_id>

  # 标记 video_compose 任务完成
  python mark_ready.py <task_id> --video-url /generated/videos/<task_id>.mp4 --episode-id <episode_id>

示例:
  python mark_ready.py abc-123 --image-url /generated/images/abc-123.png --storyboard-id sb-456
  python mark_ready.py def-456 --video-url /generated/videos/def-456.mp4 --episode-id ep-789
"""

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
READY_DIR = BASE_DIR / "generated" / "queue" / "ready"
READY_DIR.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="标记生成任务为已就绪")
    parser.add_argument("task_id", help="任务 ID")
    parser.add_argument("--image-url", help="生成的图片 URL (用于 image_gen)")
    parser.add_argument("--video-url", help="生成的视频 URL (用于 video_compose)")
    parser.add_argument("--storyboard-id", help="分镜 ID (用于 image_gen)")
    parser.add_argument("--episode-id", help="剧集 ID (用于 video_compose)")
    args = parser.parse_args()

    result = {}
    if args.image_url:
        result["image_url"] = args.image_url
    if args.video_url:
        result["video_url"] = args.video_url
    if args.storyboard_id:
        result["storyboard_id"] = args.storyboard_id
    if args.episode_id:
        result["episode_id"] = args.episode_id

    if not result:
        print("❌ 错误: 必须指定 --image-url 或 --video-url")
        sys.exit(1)

    ready_data = {
        "task_id": args.task_id,
        "result": result,
        "completed_at": __import__("datetime").datetime.now().isoformat(),
    }

    filepath = READY_DIR / f"{args.task_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(ready_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 已标记任务 {args.task_id} 为就绪状态")
    print(f"   文件: {filepath}")
    print(f"   Worker 将在下次轮询时提交到后端")


if __name__ == "__main__":
    main()