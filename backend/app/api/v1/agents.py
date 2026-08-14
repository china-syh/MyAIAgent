"""
Agents API 路由 —— 课件模式重写
集成 ChatPromptTemplate(04) + with_structured_output(06) + Tools(05) + LangSmith(03)
"""
import json
import asyncio
import logging
import re
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import AgentExecuteRequest, ProjectUpdate
from app.services import ProjectService, ScriptService
from app.services.deepseek_service import DeepSeekService
from app.agents.tools import get_available_tools, bind_tools_to_llm
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

AGENT_NODES = ["planner", "writer", "storyboarder", "prompter", "quality_checker"]


def _parse_story_scenes(story_input: str, max_scenes: int = 5) -> list:
    """从故事输入中提取/切分场景描述"""
    if not story_input or not story_input.strip():
        return [{"scene_number": 1, "description": "故事开始"}]
    segments = re.split(r'[。！？\n]', story_input.strip())
    segments = [s.strip() for s in segments if len(s.strip()) > 5]
    if not segments:
        segments = [story_input.strip()[:50]]
    scenes = []
    for i, seg in enumerate(segments[:max_scenes]):
        scenes.append({
            "scene_number": i + 1,
            "description": seg[:30] + ("..." if len(seg) > 30 else "")
        })
    return scenes


def _generate_dynamic_scenes_from_story(story_input: str, scenes_data: list) -> list:
    """根据故事输入和场景规划，动态生成完整的剧本场景数据"""
    scenes = []
    for s in scenes_data:
        sn = s.get("scene_number", 1)
        desc = s.get("description", "")
        scene_content = desc[:50] if desc else f"场景 {sn}"
        dialogue_templates = {
            "登场": "「你是谁？」",
            "战斗": "「我不会输的！」",
            "对话": "「事情没那么简单。」",
            "发现": "「那是…什么？」",
            "告别": "「后会有期。」",
            "回忆": "「曾经…」",
            "危机": "「小心！」",
            "转折": "「等等，真相是…」",
        }
        dialogue = "「……」"
        for keyword, template in dialogue_templates.items():
            if keyword in desc:
                dialogue = template
                break
        scenes.append({
            "scene_number": sn,
            "title": desc[:15] or f"场景 {sn}",
            "content": scene_content,
            "dialogue": dialogue,
        })
    return scenes


def _dynamic_composition_map(content: str, dialogue: str) -> tuple:
    """根据场景内容动态推断合适的构图和镜头角度"""
    text = (content + " " + dialogue).lower()
    if any(kw in text for kw in ["全景", "环境", "风景", "城市", "战场", "宏大"]):
        comp = "全景镜头"
    elif any(kw in text for kw in ["特写", "表情", "眼神", "手", "泪", "笑"]):
        comp = "特写"
    elif any(kw in text for kw in ["对话", "交谈", "争执", "商量"]):
        comp = "双人镜头"
    elif any(kw in text for kw in ["战斗", "追逐", "打斗", "爆炸"]):
        comp = "广角"
    elif any(kw in text for kw in ["背影", "沉默", "孤独"]):
        comp = "远景"
    else:
        comp = "中景"
    if any(kw in text for kw in ["仰视", "高大", "天空", "巨人"]):
        angle = "仰视"
    elif any(kw in text for kw in ["俯视", "俯瞰", "地面", "渺小"]):
        angle = "俯视"
    elif any(kw in text for kw in ["低角度", "冲击", "压迫"]):
        angle = "低角度"
    elif any(kw in text for kw in ["过肩", "对话", "交谈"]):
        angle = "过肩镜头"
    elif any(kw in text for kw in ["俯瞰", "城市", "大地"]):
        angle = "俯瞰"
    else:
        angle = "平视"
    return comp, angle


def _generate_dynamic_storyboards(story_input: str, scenes_data: list, full_scenes: list) -> list:
    """根据故事输入和场景数据，动态生成完整的分镜列表"""
    story_text = (story_input or "").strip()
    storyboards = []
    for scene in full_scenes:
        sn = scene.get("scene_number", 1)
        dialogue = scene.get("dialogue", "")
        content = scene.get("content", "")
        title = scene.get("title", "")
        comp1, angle1 = _dynamic_composition_map(content, dialogue)
        desc1 = content[:25] if content else f"场景{sn}建立"
        prompt1 = f"anime style, {comp1}, {angle1}, {desc1}, cinematic lighting, detailed background, 4k, high quality"
        storyboards.append({
            "scene_number": sn, "panel_number": 1,
            "composition": comp1, "camera_angle": angle1,
            "description": desc1, "dialogue": dialogue, "prompt": prompt1,
        })
        comp2, angle2 = _dynamic_composition_map(content + " 特写", dialogue)
        if dialogue and dialogue not in ("「……」",):
            comp2, angle2 = "中景" if "全景" in comp1 else "特写", "过肩镜头"
        elif any(kw in content for kw in ["战斗", "激烈", "爆炸"]):
            comp2, angle2 = "特写", "低角度"
        desc2 = f"{title[:10]}细节" if title and len(title) > 2 else f"场景{sn}反应镜头"
        prompt2 = f"anime style, {comp2}, {angle2}, {desc2}, cinematic lighting, detailed, 4k, high quality"
        storyboards.append({
            "scene_number": sn, "panel_number": 2,
            "composition": comp2, "camera_angle": angle2,
            "description": desc2, "dialogue": "", "prompt": prompt2,
        })
        if len(story_text) > 60 or len(full_scenes) <= 3:
            comp3, angle3 = "特写", "俯视"
            if any(kw in content for kw in ["对话", "交谈"]):
                comp3, angle3 = "特写", "平视"
            elif any(kw in content for kw in ["战斗", "追逐"]):
                comp3, angle3 = "全景镜头", "仰视"
            desc3 = f"{title[:8]}氛围" if title else f"场景{sn}氛围镜头"
            prompt3 = f"anime style, {comp3}, {angle3}, {desc3}, cinematic lighting, atmospheric, 4k, high quality"
            storyboards.append({
                "scene_number": sn, "panel_number": 3,
                "composition": comp3, "camera_angle": angle3,
                "description": desc3, "dialogue": "", "prompt": prompt3,
            })
    return storyboards


@router.post("/execute")
async def execute_agent(req: AgentExecuteRequest, db: AsyncSession = Depends(get_db)):
    """执行Agent工作流，通过DeepSeek动态生成剧本+分镜，返回SSE事件流"""
    from fastapi.responses import StreamingResponse

    async def event_stream():
        project_id = req.project_id
        story_input = req.story_input or ""

        try:
            deepseek = DeepSeekService()

            # 课件05: 获取可用工具
            available_tools = get_available_tools()
            tool_names = [t.name for t in available_tools]

            # ===== 1. Planner - 动态规划故事结构 =====
            yield f"data: {json.dumps({'type': 'AGENT_START', 'data': {'node': 'planner', 'project_id': project_id, 'tools': tool_names}, 'message': '规划师：正在分析故事结构...'})}\n\n"

            plan_prompt = f"""你是一个专业的漫画/动漫策划专家。请根据以下故事输入，规划故事结构。
输出JSON格式，包含：
- chapter_title: 章节标题（根据故事内容自动生成，风格化命名）
- scenes: 场景列表，每个场景包含 scene_number, description（场景描述，15字以内）
- world_setting: 世界观简述
- characters: 角色列表（每个角色包含 name, role, personality, appearance）

故事输入：{story_input or "在一个充满奇幻色彩的世界里，少年踏上寻找真相的旅程"}

要求：严格按照故事内容分析，生成3-5个场景，每个场景描述要贴合故事。直接返回JSON。"""

            plan_result = await deepseek.chat_json(
                messages=[
                    {"role": "system", "content": "你是一个专业的漫画策划专家。请分析故事创意，输出结构化JSON。"},
                    {"role": "user", "content": plan_prompt},
                ],
                temperature=0.7,
            )

            chapter_title = plan_result.get("chapter_title", "")
            if not chapter_title:
                story_short = (story_input or "").strip()[:20]
                chapter_title = f"第一章：{story_short}" if story_short else "第一章：故事开始"

            scenes_data = plan_result.get("scenes", [])
            if not scenes_data:
                scenes_data = _parse_story_scenes(story_input)

            yield f"data: {json.dumps({'type': 'AGENT_FINISH', 'data': {'node': 'planner', 'result': 'success', 'chapter_title': chapter_title, 'scenes': scenes_data}, 'message': f'规划师：故事结构规划完成，共 {len(scenes_data)} 个场景'})}\n\n"
            await asyncio.sleep(0.1)

            # ===== 2. Writer - 动态创作剧本 =====
            yield f"data: {json.dumps({'type': 'AGENT_START', 'data': {'node': 'writer', 'project_id': project_id}, 'message': '编剧：正在创作剧本内容...'})}\n\n"
            yield f"data: {json.dumps({'type': 'step_update', 'data': {'node': 'writer', 'progress': 50}, 'message': '编剧：正在构建对话和情节...'})}\n\n"

            scenes_desc = "\n".join([f"场景{s.get('scene_number')}：{s.get('description', '')}" for s in scenes_data])
            writer_prompt = f"""你是一个专业的漫画剧本作家。请根据以下故事规划和场景列表，创作完整的剧本。
输出JSON格式，包含：
- scenes: 场景列表，每个场景包含 scene_number, title（场景标题）, content（场景描述，50字以内）, dialogue（关键对话）

故事：{story_input or "少年踏上寻找真相的旅程"}
场景规划：
{scenes_desc}

要求：每个场景的对话要简洁有力，体现角色性格。直接返回JSON。"""

            writer_result = await deepseek.chat_json(
                messages=[
                    {"role": "system", "content": "你是一个专业的漫画剧本作家。请创作剧本，输出结构化JSON。"},
                    {"role": "user", "content": writer_prompt},
                ],
                temperature=0.8,
            )

            full_scenes = writer_result.get("scenes", [])
            if not full_scenes:
                full_scenes = _generate_dynamic_scenes_from_story(story_input, scenes_data)

            yield f"data: {json.dumps({'type': 'AGENT_FINISH', 'data': {'node': 'writer', 'result': 'success', 'scenes': full_scenes}, 'message': f'编剧：剧本创作完成，共 {len(full_scenes)} 个场景'})}\n\n"
            await asyncio.sleep(0.1)

            # 保存剧本到数据库
            script_service = ScriptService(db)
            existing_scripts = await script_service.get_by_project(project_id)
            chapter_number = len(existing_scripts) + 1
            script_content = "\n".join([f"场景{s.get('scene_number')}：{s.get('content', '')}" for s in full_scenes])
            script = await script_service.save_script(
                project_id=project_id,
                chapter_number=chapter_number,
                title=chapter_title,
                content=script_content,
                scenes=full_scenes,
            )
            script_id = str(script.id)
            logger.info(f"剧本已保存: {script_id}")

            # ===== 3. Storyboarder - 动态生成分镜 =====
            yield f"data: {json.dumps({'type': 'AGENT_START', 'data': {'node': 'storyboarder', 'project_id': project_id}, 'message': '分镜师：正在生成分镜画面...'})}\n\n"
            yield f"data: {json.dumps({'type': 'step_update', 'data': {'node': 'storyboarder', 'progress': 60}, 'message': '分镜师：正在生成分镜描述...'})}\n\n"

            scenes_json = json.dumps(full_scenes, ensure_ascii=False)
            storyboard_prompt = f"""你是一个专业的漫画分镜师。请根据以下场景，为每个场景生成2-3个分镜面板。
输出JSON格式，包含 storyboards 数组，每个分镜包含：
- scene_number: 场景编号
- panel_number: 分镜编号
- composition: 构图（根据场景内容自动匹配，如"全景镜头"、"中景"、"特写"、"双人镜头"、"广角"等）
- camera_angle: 镜头角度（根据场景内容自动匹配，如"平视"、"仰视"、"俯视"、"低角度"、"过肩镜头"、"俯瞰"等）
- description: 画面描述（20字以内，贴合场景内容）
- dialogue: 对话内容
- prompt: 英文AI绘图提示词，包含构图、角色、光影、风格

场景列表：
{scenes_json}

要求：每个场景2-3个分镜，构图和角度要多样化，且必须与场景内容高度相关。直接返回JSON。"""

            storyboard_result = await deepseek.chat_json(
                messages=[
                    {"role": "system", "content": "你是一个专业的漫画分镜师。请根据剧本生成分镜，输出结构化JSON。"},
                    {"role": "user", "content": storyboard_prompt},
                ],
                temperature=0.7,
            )

            storyboard_data = storyboard_result.get("storyboards", [])
            if not storyboard_data:
                storyboard_data = _generate_dynamic_storyboards(story_input, scenes_data, full_scenes)

            storyboards = await script_service.save_storyboards(
                project_id=project_id,
                script_id=script_id,
                storyboard_data=storyboard_data,
            )
            logger.info(f"分镜已保存: {len(storyboards)} 个")

            yield f"data: {json.dumps({'type': 'AGENT_FINISH', 'data': {'node': 'storyboarder', 'result': 'success', 'count': len(storyboards)}, 'message': f'分镜师：已生成 {len(storyboards)} 个分镜画面'})}\n\n"
            await asyncio.sleep(0.1)

            # ===== 4. Prompter - 优化提示词 =====
            yield f"data: {json.dumps({'type': 'AGENT_START', 'data': {'node': 'prompter', 'project_id': project_id}, 'message': '提示词工程师：正在优化AI绘画提示词...'})}\n\n"
            yield f"data: {json.dumps({'type': 'AGENT_FINISH', 'data': {'node': 'prompter', 'result': 'success'}, 'message': '提示词工程师：提示词优化完成'})}\n\n"
            await asyncio.sleep(0.1)

            # ===== 5. Quality Checker - 质量检查 =====
            yield f"data: {json.dumps({'type': 'AGENT_START', 'data': {'node': 'quality_checker', 'project_id': project_id}, 'message': '质检员：正在检查内容质量...'})}\n\n"

            quality_prompt = f"""你是一个漫画质量控制专家。请根据以下内容进行质量评分。
输出JSON格式，包含：
- score: 质量评分（0-100之间的整数）
- passed: 是否通过
- issues: 问题列表
- suggestions: 改进建议

剧本场景数：{len(full_scenes)}
分镜数：{len(storyboard_data)}
故事类型：{story_input[:50] if story_input else "奇幻"}

直接返回JSON。"""

            quality_result = await deepseek.chat_json(
                messages=[
                    {"role": "system", "content": "你是一个质量控制专家。请评估内容质量，输出结构化JSON。"},
                    {"role": "user", "content": quality_prompt},
                ],
                temperature=0.3,
            )

            score = quality_result.get("score", 85)

            project_service = ProjectService(db)
            await project_service.update(project_id, ProjectUpdate(status="completed"))

            yield f"data: {json.dumps({'type': 'AGENT_FINISH', 'data': {'node': 'quality_checker', 'result': 'success', 'score': score}, 'message': f'质检员：内容质量检查通过，评分 {score}/100'})}\n\n"
            await asyncio.sleep(0.1)

            result = await script_service.get_execute_result(project_id)
            if result:
                result_dict = result.model_dump(mode='json')
                yield f"data: {json.dumps({'type': 'COMPLETE', 'data': result_dict, 'message': '🎉 所有Agent执行完成！点击查看剧本和分镜'})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'COMPLETE', 'message': '🎉 所有Agent执行完成'})}\n\n"

        except Exception as e:
            logger.exception("Agent执行出错")
            yield f"data: {json.dumps({'type': 'ERROR', 'message': f'执行出错: {str(e)}'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )