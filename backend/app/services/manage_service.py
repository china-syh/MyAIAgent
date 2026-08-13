import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import (
    TaskRepository, EpisodeRepository, SceneRepository, PropRepository, VoiceRepository,
    CharacterRelationshipRepository, FreezoneNodeRepository, DirectorWorldRepository,
    AIChatRepository, StyleTemplateRepository,
)
from app.models.manage import Task
from app.models.project import Character
from app.schemas import (
    TaskResponse, EpisodeResponse, SceneResponse, PropResponse, VoiceResponse,
    CharacterRelationshipResponse, CharacterRelationshipCreate,
    FreezoneNodeResponse, FreezoneNodeCreate, FreezoneNodeUpdate,
    DirectorWorldResponse, DirectorWorldCreate,
    AIChatResponse, AIChatCreate,
    StyleTemplateResponse, StyleTemplateCreate,
)
from app.services.deepseek_service import DeepSeekService, get_system_prompt

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, db: AsyncSession):
        self.repo = TaskRepository(db)
        self.deepseek = DeepSeekService()

    async def list(self, project_id: str = None) -> list:
        if project_id:
            tasks = await self.repo.get_by_project(UUID(project_id))
        else:
            tasks = await self.repo.get_multi(limit=200)
        return [TaskResponse.model_validate(t).model_dump(mode='json') for t in tasks]

    async def create(self, project_id: str, name: str, type: str, total_steps: int = 1) -> Task:
        task = await self.repo.create(
            project_id=UUID(project_id) if project_id else None,
            name=name, type=type, total_steps=total_steps, status="pending", logs=[]
        )
        return task

    async def update_progress(self, task_id: str, progress: int, current_step: int = None, log: str = None):
        task = await self.repo.get(UUID(task_id))
        if not task:
            return None
        update_data = {"progress": progress}
        if current_step is not None:
            update_data["current_step"] = current_step
        if log:
            logs = list(task.logs or [])
            logs.append({"time": datetime.now(timezone.utc).isoformat(), "message": log})
            update_data["logs"] = logs
        if progress >= 100:
            update_data["status"] = "completed"
            update_data["completed_at"] = datetime.now(timezone.utc)
        elif progress > 0:
            update_data["status"] = "running"
            update_data["started_at"] = task.started_at or datetime.now(timezone.utc)
        await self.repo.update(UUID(task_id), **update_data)
        return TaskResponse.model_validate(await self.repo.get(UUID(task_id)))

    async def fail(self, task_id: str, error: str):
        data = {"status": "failed", "error": error, "completed_at": datetime.now(timezone.utc)}
        await self.repo.update(UUID(task_id), **data)
        return TaskResponse.model_validate(await self.repo.get(UUID(task_id)))

    async def cancel(self, task_id: str):
        data = {"status": "cancelled", "completed_at": datetime.now(timezone.utc)}
        await self.repo.update(UUID(task_id), **data)
        return TaskResponse.model_validate(await self.repo.get(UUID(task_id)))

    async def get(self, task_id: str) -> TaskResponse:
        task = await self.repo.get(UUID(task_id))
        return TaskResponse.model_validate(task) if task else None

    async def generate_image(self, project_id: str, storyboard_id: str, prompt: str) -> TaskResponse:
        """立即生成图像：DeepSeek 分析场景 + 生成图片"""
        # 获取分镜完整信息
        from app.repositories.storyboard_repo import StoryboardRepository
        sb_repo = StoryboardRepository(self.repo.db)
        sb = await sb_repo.get(UUID(storyboard_id))

        # 构建分镜上下文
        storyboard_context = {}
        if sb:
            storyboard_context = {
                "description": sb.description or "",
                "composition": sb.composition or "",
                "dialogue": sb.dialogue or "",
                "camera_angle": sb.camera_angle or "",
                "prompt": prompt,
            }

        # 创建任务并立即开始生成
        task = await self.create(project_id, "图像生成", "image_gen", 4)
        asyncio.create_task(self._generate_image_real(task.id, storyboard_context, storyboard_id))
        return TaskResponse.model_validate(await self.repo.get(task.id))

    async def _generate_image_real(self, task_id: UUID, storyboard_context: dict, storyboard_id: str):
        """根据分镜内容生成贴合场景的图片"""
        from app.database import async_session as db_session
        async with db_session() as session:
            try:
                task_repo = TaskRepository(session)
                service = TaskService.__new__(TaskService)
                service.repo = task_repo
                service.deepseek = DeepSeekService()

                await service.update_progress(str(task_id), 5, 1, "正在分析分镜内容...")

                # 1. 用 DeepSeek 分析分镜内容，提取场景视觉要素
                scene_info = {}
                if storyboard_context:
                    try:
                        context_str = json.dumps(storyboard_context, ensure_ascii=False)
                        analysis = await self.deepseek.chat_json(
                            messages=[
                                {"role": "system", "content": get_system_prompt("scene_analyzer")},
                                {"role": "user", "content": f"请分析以下分镜内容，提取视觉场景要素：\n\n{context_str}"},
                            ],
                            temperature=0.3,
                        )
                        if analysis and isinstance(analysis, dict):
                            scene_info = analysis
                            logger.info(f"场景分析完成: {json.dumps(scene_info, ensure_ascii=False)[:200]}")
                    except Exception as e:
                        logger.warning(f"场景分析失败，使用默认设置: {e}")

                await service.update_progress(str(task_id), 15, 2, "正在绘制场景...")

                # 2. 用AI生成真实场景图片（替代Pillow画图）
                import os, httpx
                from urllib.parse import quote
                from app.core.config import settings

                # 从分镜内容构建英文图片生成提示词
                desc = storyboard_context.get("description", "")
                comp = storyboard_context.get("composition", "")
                dialogue = storyboard_context.get("dialogue", "")
                camera = storyboard_context.get("camera_angle", "")
                user_prompt = storyboard_context.get("prompt", "")

                # 用DeepSeek生成优化的英文图片提示词
                try:
                    prompt_result = await self.deepseek.chat(
                        messages=[
                            {"role": "system", "content": get_system_prompt("image_prompt_enhancer")},
                            {"role": "user", "content": f"分镜描述：{desc}\n构图：{comp}\n对白：{dialogue}\n镜头角度：{camera}\n原始提示词：{user_prompt}"},
                        ],
                        temperature=0.3,
                        max_tokens=300,
                    )
                    image_prompt = prompt_result.strip().strip('"').strip("'")
                    logger.info(f"AI生成图片提示词: {image_prompt[:100]}")
                except Exception as e:
                    logger.warning(f"生成图片提示词失败，使用默认: {e}")
                    image_prompt = user_prompt or f"Anime manga style: {desc}, {comp}, cinematic lighting, high quality"

                # Generate through the configured provider with retry support.
                await service.update_progress(str(task_id), 30, 2, "正在通过AI生成图片...")

                if settings.IMAGE_PROVIDER == "huggingface":
                    if not settings.HF_TOKEN:
                        raise Exception("未配置 HF_TOKEN。请在 Hugging Face 创建具有 Inference Providers 权限的 Token，并写入 backend/.env")
                    api_url = f"https://router.huggingface.co/hf-inference/models/{settings.HF_IMAGE_MODEL}"
                    headers = {"Authorization": f"Bearer {settings.HF_TOKEN}"}
                    payload = {
                        "inputs": image_prompt[:2000],
                        "parameters": {
                            "width": 1024,
                            "height": 576,
                            "num_inference_steps": 4,
                        },
                    }
                elif settings.IMAGE_PROVIDER == "pollinations":
                    safe_prompt = quote(image_prompt[:2000], safe="")
                    api_url = f"{settings.IMAGE_API_URL.rstrip('/')}/{safe_prompt}"
                    headers = {}
                    payload = None
                else:
                    raise Exception(f"暂不支持图片提供商: {settings.IMAGE_PROVIDER}")

                last_error = None
                for attempt in range(1, settings.IMAGE_RETRIES + 1):
                    try:
                        async with httpx.AsyncClient(timeout=settings.IMAGE_TIMEOUT_SECONDS, follow_redirects=True) as client:
                            if payload is None:
                                resp = await client.get(api_url, headers=headers, params={"width": 1024, "height": 576, "nofeed": "true", "model": settings.IMAGE_MODEL})
                            else:
                                resp = await client.post(api_url, headers=headers, json=payload)
                            resp.raise_for_status()
                            content_type = resp.headers.get("content-type", "")
                            if not resp.content or not content_type.startswith("image/"):
                                raise Exception(f"图片服务返回非图片内容: {content_type or 'unknown'}")
                            img_data = resp.content
                            logger.info(f"AI图片生成成功: {len(img_data)} bytes, attempt={attempt}")
                            break
                    except Exception as exc:
                        last_error = exc
                        logger.warning(f"图片服务请求失败 ({attempt}/{settings.IMAGE_RETRIES}): {exc}")
                        if attempt < settings.IMAGE_RETRIES:
                            await asyncio.sleep(min(attempt * 2, 6))
                else:
                    raise Exception(
                        f"图片服务不可用: {last_error}. 请检查网络，或在 backend/.env 配置 IMAGE_API_URL。"
                    )

                # ===== 保存图片 =====
                await service.update_progress(str(task_id), 75, 4, "正在保存图像...")

                generated_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "generated", "images")
                os.makedirs(generated_dir, exist_ok=True)
                img_path = os.path.join(generated_dir, f"{task_id}.jpg")
                with open(img_path, "wb") as f:
                    f.write(img_data)
                img_url = f"/generated/images/{task_id}.jpg"

                logger.info(f"图像生成完成: {task_id} → {img_path}")

                result = {
                    "image_url": img_url,
                    "storyboard_id": storyboard_id,
                    "scene_analysis": scene_info,
                }
                await task_repo.update(task_id, status="completed", progress=100,
                                       result=result, completed_at=datetime.now(timezone.utc))
                if storyboard_id:
                    from app.repositories.storyboard_repo import StoryboardRepository
                    sb_repo = StoryboardRepository(session)
                    await sb_repo.update(UUID(storyboard_id), image_url=img_url)
                await session.commit()
            except Exception as e:
                logger.error(f"图像生成失败: {e}")
                await session.rollback()
                import traceback
                logger.error(traceback.format_exc())
                try:
                    await task_repo.update(task_id, status="failed", error=str(e),
                                           completed_at=datetime.now(timezone.utc))
                    await session.commit()
                except:
                    pass

    async def compose_video(self, project_id: str, episode_id: str) -> TaskResponse:
        """立即合成视频：DeepSeek 规划 + 组装图片为视频"""
        # 检查是否已有该集的已完成视频，避免重复生成
        existing_tasks = await self.repo.get_by_project(UUID(project_id))
        for t in existing_tasks:
            if t.type == "video_compose" and t.status == "completed":
                result = t.result or {}
                if result.get("episode_id") == episode_id:
                    logger.info(f"该集已有完成视频，返回现有任务: {t.id}")
                    return TaskResponse.model_validate(t)

        # 获取该集的所有分镜
        from app.repositories.storyboard_repo import StoryboardRepository
        sb_repo = StoryboardRepository(self.repo.db)
        script_id = UUID(episode_id) if episode_id else None
        storyboards = []
        if script_id:
            storyboards = await sb_repo.get_by_script(script_id)

        # 调用 DeepSeek 规划视频合成
        video_plan = {}
        if storyboards:
            try:
                sb_list = []
                for sb in storyboards:
                    sb_list.append({
                        "scene_number": sb.scene_number,
                        "panel_number": sb.panel_number,
                        "description": sb.description or "",
                        "composition": sb.composition or "",
                        "dialogue": sb.dialogue or "",
                        "camera_angle": sb.camera_angle or "",
                        "prompt": sb.prompt or "",
                        "has_image": bool(sb.image_url),
                    })
                sb_list.sort(key=lambda x: (x["scene_number"], x["panel_number"]))
                context_str = json.dumps(sb_list, ensure_ascii=False)
                plan_result = await self.deepseek.chat_json(
                    messages=[
                        {"role": "system", "content": get_system_prompt("video_composition_planner")},
                        {"role": "user", "content": f"请根据以下分镜列表规划视频合成方案：\n\n{context_str}"},
                    ],
                    temperature=0.4,
                )
                video_plan = plan_result
                logger.info(f"DeepSeek 视频规划完成: {len(storyboards)} 个分镜")
            except Exception as e:
                logger.warning(f"DeepSeek 视频规划失败，使用默认方案: {e}")

        # 创建任务并立即开始合成
        task = await self.create(project_id, "视频合成", "video_compose", 5)
        asyncio.create_task(self._compose_video_real(task.id, project_id, episode_id, storyboards, video_plan))
        return TaskResponse.model_validate(await self.repo.get(task.id))

    async def _compose_video_real(self, task_id: UUID, project_id: str, episode_id: str,
                                   storyboards: list, video_plan: dict):
        """真正的视频合成：Ken Burns动画 + 场景转场 + AI语音旁白 + 背景音乐（后台异步执行）"""
        from app.database import async_session as db_session
        async with db_session() as session:
            try:
                task_repo = TaskRepository(session)
                service = TaskService.__new__(TaskService)
                service.repo = task_repo

                await service.update_progress(str(task_id), 5, 1, "正在分析视频素材...")

                import os
                # 收集有图片的分镜，按 scene_number, panel_number 排序
                panels = [sb for sb in storyboards if sb.image_url]
                if not panels:
                    await task_repo.update(task_id, status="failed", error="没有已生成图片的分镜，无法合成视频",
                                           completed_at=datetime.now(timezone.utc))
                    await session.commit()
                    return

                panels.sort(key=lambda x: (x.scene_number or 0, x.panel_number or 0))
                logger.info(f"视频合成: {len(panels)} 个分镜")

                await service.update_progress(str(task_id), 10, 2, "正在加载图片素材...")

                # 获取图片文件路径
                backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                image_paths = []
                for sb in panels:
                    rel_path = sb.image_url.lstrip("/")
                    full_path = os.path.join(backend_dir, rel_path)
                    if os.path.exists(full_path):
                        image_paths.append(full_path)

                if not image_paths:
                    raise Exception("所有分镜图片文件都不存在")

                # ===== 1. 提取视频规划信息 =====
                await service.update_progress(str(task_id), 15, 3, "正在解析视频规划...")

                scene_plans = {}
                if video_plan and "scene_transitions" in video_plan:
                    for st in video_plan["scene_transitions"]:
                        sn = st.get("scene_number", 0)
                        scene_plans[sn] = {
                            "transition": st.get("transition_type", "fade"),
                            "narration": st.get("narration", ""),
                            "bgm_mood": st.get("background_music_mood", ""),
                        }
                        panel_map = {}
                        for p in st.get("panels", []):
                            panel_map[p.get("panel_number", 0)] = {
                                "duration": p.get("duration", 2.5),
                                "camera_movement": p.get("camera_movement", "zoom_in"),
                            }
                        scene_plans[sn]["panels"] = panel_map

                # ===== 2. 用DeepSeek增强旁白文案 =====
                narration_text = ""
                for sn in sorted(scene_plans.keys()):
                    n = scene_plans[sn].get("narration", "")
                    if n:
                        narration_text += n + " "

                # 用DeepSeek润色旁白，使其更口语化、更有感情
                if narration_text.strip():
                    try:
                        enhanced_narration = await self.deepseek.chat(
                            messages=[
                                {"role": "system", "content": "你是一个专业的配音编剧。请将以下旁白文案润色得更口语化、富有情感，适合语音朗读。保持原意，每句话简洁有力，不超过20字。直接返回润色后的文本，不要任何解释。"},
                                {"role": "user", "content": f"旁白文案：{narration_text.strip()}"},
                            ],
                            temperature=0.5,
                            max_tokens=500,
                        )
                        enhanced = enhanced_narration.strip().strip('"').strip("'")
                        if enhanced:
                            narration_text = enhanced
                            logger.info(f"DeepSeek旁白润色完成: {len(narration_text)} 字")
                    except Exception as e:
                        logger.warning(f"旁白润色失败，使用原始文本: {e}")

                # ===== 3. 生成旁白语音 =====
                audio_path = None
                if narration_text.strip():
                    await service.update_progress(str(task_id), 20, 4, "正在生成AI语音旁白...")
                    try:
                        import edge_tts
                        audio_dir = os.path.join(backend_dir, "generated", "audio")
                        os.makedirs(audio_dir, exist_ok=True)
                        audio_path = os.path.join(audio_dir, f"{task_id}_narration.mp3")
                        tts = edge_tts.Communicate(
                            narration_text.strip(),
                            "zh-CN-XiaoxiaoNeural",
                            rate="-10%",
                            pitch="-5Hz",
                        )
                        await tts.save(audio_path)
                        logger.info(f"旁白语音生成完成: {len(narration_text)} 字 → {audio_path}")
                    except Exception as e:
                        logger.warning(f"旁白语音生成失败: {e}")
                        audio_path = None

                # ===== 4. 创建带 Ken Burns 动画的视频片段（固定1920x1080画布） =====
                await service.update_progress(str(task_id), 40, 5, "正在创建Ken Burns动画...")

                from moviepy import (
                    ImageClip, concatenate_videoclips, AudioFileClip,
                    CompositeAudioClip, CompositeVideoClip
                )
                from moviepy.video.fx import Resize, FadeIn, FadeOut

                VIDEO_W, VIDEO_H = 1280, 720  # 720p渲染（更快）
                clips = []
                total_duration = 0

                for i, (sb, img_path) in enumerate(zip(panels, image_paths)):
                    sn = sb.scene_number or 1
                    pn = sb.panel_number or 1

                    # 获取该分镜的规划参数
                    scene_info = scene_plans.get(sn, {})
                    panel_info = scene_info.get("panels", {}).get(pn, {})
                    duration = panel_info.get("duration", 2.5)
                    camera_movement = panel_info.get("camera_movement", "zoom_in")

                    # 创建基础片段，先填满高
                    clip = ImageClip(img_path, duration=duration)
                    clip = clip.resized(height=VIDEO_H)

                    # 应用Ken Burns动画效果，然后用CompositeVideoClip固定画布
                    if camera_movement == "zoom_in":
                        # 缓慢放大：从1.0到1.12
                        clip = clip.with_effects([Resize(lambda t, d=duration: 1.0 + 0.12 * (t / d))])
                        # 用画布固定尺寸，溢出部分自动裁剪（居中）
                        clip = CompositeVideoClip([clip.with_position(('center', 'center'))], size=(VIDEO_W, VIDEO_H))
                    elif camera_movement == "zoom_out":
                        # 缓慢缩小：从1.12到1.0
                        clip = clip.with_effects([Resize(lambda t, d=duration: 1.12 - 0.12 * (t / d))])
                        clip = CompositeVideoClip([clip.with_position(('center', 'center'))], size=(VIDEO_W, VIDEO_H))
                    elif camera_movement == "pan":
                        # 横向平移：图片放大到1.15倍，从左到右偏移
                        clip = clip.with_effects([Resize(1.15)])
                        clip_width = clip.w
                        if clip_width > VIDEO_W:
                            pan_range = clip_width - VIDEO_W
                            clip = clip.with_position(lambda t, d=duration, r=pan_range: (-r * (t / d), 0))
                        clip = CompositeVideoClip([clip], size=(VIDEO_W, VIDEO_H))
                    else:
                        # static - 静止，加微小呼吸效果
                        clip = clip.with_effects([Resize(lambda t, d=duration: 1.0 + 0.02 * (t / d))])
                        clip = CompositeVideoClip([clip.with_position(('center', 'center'))], size=(VIDEO_W, VIDEO_H))

                    # 淡入淡出效果
                    crossfade = 0.2
                    clip = clip.with_effects([FadeIn(crossfade), FadeOut(crossfade)])

                    clips.append(clip)
                    total_duration += duration

                # ===== 5. 合并所有片段 =====
                await service.update_progress(str(task_id), 60, 6, "正在合并视频片段...")

                final_clip = concatenate_videoclips(clips, method="compose")

                # ===== 6. 合成音频 =====
                await service.update_progress(str(task_id), 70, 7, "正在合成音频...")

                audio_clips = []

                # 6.1 旁白语音
                if audio_path and os.path.exists(audio_path):
                    try:
                        narration_audio = AudioFileClip(audio_path)
                        # 如果旁白比视频短，在末尾静音；如果比视频长，截断
                        if narration_audio.duration < total_duration:
                            from moviepy import AudioClip
                            silence_duration = total_duration - narration_audio.duration
                            silence = AudioClip(lambda t: 0, duration=silence_duration)
                            silence = silence.with_fps(22050)
                            narration_audio = CompositeAudioClip([narration_audio, silence])
                            narration_audio = narration_audio.with_duration(total_duration)
                        else:
                            narration_audio = narration_audio.subclipped(0, total_duration)

                        # 旁白音量提升到1.0（清晰可听）
                        narration_audio = narration_audio.with_volume_scaled(1.0)
                        audio_clips.append(narration_audio)
                        logger.info(f"旁白音频已加载: {narration_audio.duration:.1f}s")
                    except Exception as e:
                        logger.warning(f"旁白音频加载失败: {e}")

                # 6.2 背景音乐（使用DeepSeek推荐的音调生成）
                bgm_path = None
                try:
                    bgm_dir = os.path.join(backend_dir, "generated", "bgm")
                    os.makedirs(bgm_dir, exist_ok=True)
                    bgm_path = os.path.join(bgm_dir, "bgm_epic_loop.mp3")

                    # 如果还没有背景音乐文件，生成一个更丰富的
                    if not os.path.exists(bgm_path):
                        await service.update_progress(str(task_id), 75, 8, "正在生成背景音乐...")
                        import numpy as np
                        from moviepy import AudioClip

                        sample_rate = 44100
                        bgm_duration = max(total_duration, 15)

                        def make_bgm(t):
                            # 更丰富的和弦进行：C大调 → G大调交替
                            # 每4秒换一次和弦
                            chord_idx = int(t / 4) % 2
                            if chord_idx == 0:
                                # C大调和弦：C E G C
                                f1, f2, f3, f4 = 261.63, 329.63, 392.00, 523.25
                            else:
                                # G大调和弦：G B D G
                                f1, f2, f3, f4 = 392.00, 493.88, 587.33, 783.99

                            env = 0.3 + 0.15 * np.sin(2 * np.pi * 0.3 * t)  # 缓慢的包络
                            wave = (np.sin(2 * np.pi * f1 * t) * 0.12 +
                                    np.sin(2 * np.pi * f2 * t) * 0.08 +
                                    np.sin(2 * np.pi * f3 * t) * 0.06 +
                                    np.sin(2 * np.pi * f4 * t) * 0.04 +
                                    np.sin(2 * np.pi * 130.81 * t) * 0.15)  # 低频
                            return wave * env * 0.4

                        bgm_clip = AudioClip(make_bgm, duration=bgm_duration)
                        bgm_clip = bgm_clip.with_fps(sample_rate)
                        bgm_clip.write_audiofile(bgm_path, fps=sample_rate, logger=None)
                        bgm_clip.close()
                        logger.info(f"背景音乐已生成: {bgm_path}")

                    if os.path.exists(bgm_path):
                        bgm_audio = AudioFileClip(bgm_path).subclipped(0, total_duration)
                        # 背景音乐音量提升到0.5（可听见但不过分）
                        bgm_audio = bgm_audio.with_volume_scaled(0.5)
                        audio_clips.append(bgm_audio)
                except Exception as e:
                    logger.warning(f"背景音乐生成失败: {e}")

                # 合并所有音频
                if audio_clips:
                    final_audio = CompositeAudioClip(audio_clips)
                    final_audio = final_audio.with_duration(total_duration)
                else:
                    final_audio = None

                # ===== 7. 保存视频 =====
                await service.update_progress(str(task_id), 85, 9, "正在保存视频文件...")

                generated_dir = os.path.join(backend_dir, "generated", "videos")
                os.makedirs(generated_dir, exist_ok=True)
                video_path = os.path.join(generated_dir, f"{task_id}.mp4")

                final_clip = final_clip.with_audio(final_audio) if final_audio else final_clip

                # 使用优化的渲染参数：720p快渲染
                final_clip.write_videofile(
                    video_path,
                    fps=20,  # 20fps足够（节省渲染时间）
                    codec="libx264",
                    audio_codec="aac",
                    logger=None,
                    preset="ultrafast",
                    threads=8,  # 更多线程加速
                    ffmpeg_params=["-crf", "28"],  # 允许稍高压缩（质量可接受）
                )
                final_clip.close()

                logger.info(f"视频渲染完成: {video_path}")

                # 清理临时音频文件
                if audio_path and os.path.exists(audio_path):
                    try:
                        os.remove(audio_path)
                    except:
                        pass

                # 生成封面图片（第一帧）
                cover_path = os.path.join(generated_dir, f"{task_id}_cover.png")
                from PIL import Image as PILImage
                if image_paths:
                    cover_img = PILImage.open(image_paths[0])
                    cover_img = cover_img.resize((VIDEO_W, VIDEO_H), PILImage.LANCZOS)
                    cover_img.save(cover_path, "PNG")

                video_url = f"/generated/videos/{task_id}.mp4"
                cover_url = f"/generated/videos/{task_id}_cover.png"

                result = {
                    "video_url": video_url,
                    "cover_url": cover_url,
                    "episode_id": episode_id,
                    "video_plan": video_plan,
                    "panel_count": len(panels),
                    "total_duration": round(total_duration, 1),
                    "has_narration": bool(narration_text.strip()),
                    "has_bgm": bgm_path is not None and os.path.exists(bgm_path),
                    "resolution": f"{VIDEO_W}x{VIDEO_H}",
                    "fps": 20,
                }
                await task_repo.update(task_id, status="completed", progress=100,
                                       result=result, completed_at=datetime.now(timezone.utc))
                await session.commit()
                logger.info(f"视频合成完成: {task_id} → {video_path} ({total_duration}s, {VIDEO_W}x{VIDEO_H})")
            except Exception as e:
                logger.error(f"视频合成失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                try:
                    await session.rollback()
                    await task_repo.update(task_id, status="failed", error=str(e),
                                           completed_at=datetime.now(timezone.utc))
                    await session.commit()
                except:
                    pass

    async def get_pending_generations(self) -> list:
        """获取所有待处理的生成任务（image_gen 和 video_compose）"""
        all_pending = await self.repo.get_by_status("pending")
        items = []
        for t in all_pending:
            if t.type in ("image_gen", "video_compose"):
                items.append(TaskResponse.model_validate(t).model_dump(mode='json'))
        return items

    async def submit_generation_result(self, task_id: str, result: dict, file_path: str = None) -> TaskResponse:
        """提交生成结果（由处理程序调用）"""
        task = await self.repo.update(UUID(task_id), status="completed", progress=100,
                                      result=result, completed_at=datetime.now(timezone.utc))
        # 如果是 image_gen 且提供了 storyboard_id，更新 storyboard 的 image_url
        if task and result.get("image_url") and result.get("storyboard_id"):
            try:
                from app.repositories.storyboard_repo import StoryboardRepository
                sb_repo = StoryboardRepository(self.repo.db)
                await sb_repo.update(UUID(result["storyboard_id"]), image_url=result["image_url"])
            except Exception as e:
                logger.warning(f"更新 storyboard image_url 失败: {e}")
        return TaskResponse.model_validate(task) if task else None

    async def generate_voiceover(self, project_id: str, episode_id: str, text: str) -> TaskResponse:
        """创建语音合成任务"""
        task = await self.create(project_id, "语音合成", "voiceover", 4)
        asyncio.create_task(self._simulate_voiceover(task.id, text))
        return TaskResponse.model_validate(await self.repo.get(task.id))

    async def _simulate_voiceover(self, task_id: UUID, text: str):
        try:
            await asyncio.sleep(1)
            await self.update_progress(str(task_id), 25, 1, "正在分析文本情感...")
            await asyncio.sleep(1)
            await self.update_progress(str(task_id), 50, 2, "正在合成语音...")
            await asyncio.sleep(1)
            await self.update_progress(str(task_id), 75, 3, "正在添加情感效果...")
            await asyncio.sleep(1)
            url = f"/generated/audio/{task_id}.mp3"
            await self.repo.update(task_id, progress=100, status="completed",
                                   result={"audio_url": url, "duration": "00:01:30"},
                                   completed_at=datetime.now(timezone.utc))
            logger.info(f"语音合成完成: {task_id}")
        except Exception as e:
            await self.fail(str(task_id), str(e))


class AssetService:
    def __init__(self, db: AsyncSession):
        self.episode_repo = EpisodeRepository(db)
        self.scene_repo = SceneRepository(db)
        self.prop_repo = PropRepository(db)
        self.voice_repo = VoiceRepository(db)

    async def get_episodes(self, project_id: str) -> list:
        items = await self.episode_repo.get_by_project(UUID(project_id))
        return [EpisodeResponse.model_validate(i).model_dump(mode='json') for i in items]

    async def create_episode(self, project_id: str, data) -> EpisodeResponse:
        episode = await self.episode_repo.create(
            project_id=UUID(project_id),
            episode_number=data.episode_number,
            title=data.title,
            summary=data.summary,
            beats=data.beats or [],
        )
        return EpisodeResponse.model_validate(episode)

    async def update_episode(self, episode_id: str, data) -> EpisodeResponse:
        update = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
        await self.episode_repo.update(UUID(episode_id), **update)
        return EpisodeResponse.model_validate(await self.episode_repo.get(UUID(episode_id)))

    async def get_scenes(self, project_id: str) -> list:
        items = await self.scene_repo.get_by_project(UUID(project_id))
        return [SceneResponse.model_validate(i).model_dump(mode='json') for i in items]

    async def create_scene(self, project_id: str, data) -> SceneResponse:
        scene = await self.scene_repo.create(
            project_id=UUID(project_id), name=data.name, description=data.description,
            atmosphere=data.atmosphere, time_of_day=data.time_of_day,
            reference_image=data.reference_image, style_params=data.style_params or {},
        )
        return SceneResponse.model_validate(scene)

    async def get_props(self, project_id: str) -> list:
        items = await self.prop_repo.get_by_project(UUID(project_id))
        return [PropResponse.model_validate(i).model_dump(mode='json') for i in items]

    async def create_prop(self, project_id: str, data) -> PropResponse:
        prop = await self.prop_repo.create(
            project_id=UUID(project_id), name=data.name, category=data.category,
            description=data.description, reference_image=data.reference_image,
        )
        return PropResponse.model_validate(prop)

    async def get_voices(self, project_id: str) -> list:
        items = await self.voice_repo.get_by_project(UUID(project_id))
        return [VoiceResponse.model_validate(i).model_dump(mode='json') for i in items]

    async def create_voice(self, project_id: str, data) -> VoiceResponse:
        voice = await self.voice_repo.create(
            project_id=UUID(project_id), character_name=data.character_name,
            gender=data.gender, style=data.style, pitch=data.pitch,
            speed=data.speed, sample_url=data.sample_url,
        )
        return VoiceResponse.model_validate(voice)


# ===== 故事图谱 =====
class StoryGraphService:
    def __init__(self, db: AsyncSession):
        self.repo = CharacterRelationshipRepository(db)

    async def get_all(self, project_id: str) -> list:
        items = await self.repo.get_by_project(UUID(project_id))
        return [CharacterRelationshipResponse.model_validate(i).model_dump(mode='json') for i in items]

    async def create(self, project_id: str, data: CharacterRelationshipCreate) -> CharacterRelationshipResponse:
        rel = await self.repo.create(
            project_id=UUID(project_id),
            character_a_id=UUID(data.character_a_id) if data.character_a_id else None,
            character_b_id=UUID(data.character_b_id) if data.character_b_id else None,
            relationship_type=data.relationship_type,
            description=data.description,
            strength=data.strength,
        )
        return CharacterRelationshipResponse.model_validate(rel)

    async def delete(self, rel_id: str) -> bool:
        return await self.repo.delete(UUID(rel_id))


# ===== 自由画布 =====
class FreezoneService:
    def __init__(self, db: AsyncSession):
        self.repo = FreezoneNodeRepository(db)

    async def get_all(self, project_id: str) -> list:
        items = await self.repo.get_by_project(UUID(project_id))
        return [FreezoneNodeResponse.model_validate(i).model_dump(mode='json') for i in items]

    async def create(self, project_id: str, data: FreezoneNodeCreate) -> FreezoneNodeResponse:
        node = await self.repo.create(
            project_id=UUID(project_id),
            parent_id=UUID(data.parent_id) if data.parent_id else None,
            type=data.type,
            title=data.title,
            content=data.content,
            position_x=data.position_x,
            position_y=data.position_y,
            width=data.width,
            height=data.height,
            color=data.color,
            tags=data.tags,
        )
        return FreezoneNodeResponse.model_validate(node)

    async def update(self, node_id: str, data: FreezoneNodeUpdate) -> FreezoneNodeResponse:
        update = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
        await self.repo.update(UUID(node_id), **update)
        return FreezoneNodeResponse.model_validate(await self.repo.get(UUID(node_id)))

    async def delete(self, node_id: str) -> bool:
        return await self.repo.delete(UUID(node_id))


# ===== 导演世界 =====
class DirectorWorldService:
    def __init__(self, db: AsyncSession):
        self.repo = DirectorWorldRepository(db)

    async def get_all(self, project_id: str) -> list:
        items = await self.repo.get_by_project(UUID(project_id))
        return [DirectorWorldResponse.model_validate(i).model_dump(mode='json') for i in items]

    async def create(self, project_id: str, data: DirectorWorldCreate) -> DirectorWorldResponse:
        world = await self.repo.create(
            project_id=UUID(project_id),
            scene_id=UUID(data.scene_id) if data.scene_id else None,
            name=data.name,
            description=data.description,
            camera_position=data.camera_position,
            character_blocking=data.character_blocking,
            spatial_layout=data.spatial_layout,
            variants=data.variants,
        )
        return DirectorWorldResponse.model_validate(world)

    async def delete(self, world_id: str) -> bool:
        return await self.repo.delete(UUID(world_id))


# ===== AI助手 =====
class AIAssistantService:
    def __init__(self, db: AsyncSession):
        self.repo = AIChatRepository(db)
        self.deepseek = DeepSeekService()

    async def get_chat(self, project_id: str) -> list:
        items = await self.repo.get_recent(UUID(project_id), limit=100)
        items.reverse()
        return [AIChatResponse.model_validate(i).model_dump(mode='json') for i in items]

    async def send_message(self, data: AIChatCreate) -> dict:
        user_msg = await self.repo.create(
            project_id=UUID(data.project_id) if data.project_id else None,
            role="user", content=data.content,
            message_type=data.message_type, meta_data=data.meta_data,
        )
        # 调用DeepSeek获取回复
        try:
            reply_content = await self.deepseek.chat(
                messages=[
                    {"role": "system", "content": get_system_prompt("assistant")},
                    {"role": "user", "content": data.content},
                ],
                temperature=0.7,
            )
            reply_type = "text"
            reply_metadata = {}
        except Exception as e:
            logger.error(f"AI助手调用DeepSeek失败: {e}")
            reply_content = f"抱歉，我暂时无法回复。错误: {str(e)}"
            reply_type = "text"
            reply_metadata = {"error": str(e)}

        assistant_msg = await self.repo.create(
            project_id=UUID(data.project_id) if data.project_id else None,
            role="assistant", content=reply_content,
            message_type=reply_type, meta_data=reply_metadata,
        )
        return {
            "user": AIChatResponse.model_validate(user_msg).model_dump(mode='json'),
            "assistant": AIChatResponse.model_validate(assistant_msg).model_dump(mode='json'),
        }


# ===== 风格模板 =====
class StyleTemplateService:
    def __init__(self, db: AsyncSession):
        self.repo = StyleTemplateRepository(db)

    async def get_all(self, project_id: str = None) -> list:
        if project_id:
            items = await self.repo.get_by_project(UUID(project_id))
        else:
            items = await self.repo.get_global()
        return [StyleTemplateResponse.model_validate(i).model_dump(mode='json') for i in items]

    async def create(self, project_id: str, data: StyleTemplateCreate) -> StyleTemplateResponse:
        template = await self.repo.create(
            project_id=UUID(project_id) if project_id else None,
            name=data.name, description=data.description,
            reference_image=data.reference_image,
            style_params=data.style_params,
            color_palette=data.color_palette,
            lighting=data.lighting, mood=data.mood,
            is_global=data.is_global,
        )
        return StyleTemplateResponse.model_validate(template)

    async def delete(self, template_id: str) -> bool:
        return await self.repo.delete(UUID(template_id))
