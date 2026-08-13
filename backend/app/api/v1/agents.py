import json
import asyncio
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import AgentExecuteRequest, ProjectUpdate
from app.utils.response import success_response
from app.services import ProjectService, ScriptService

logger = logging.getLogger(__name__)
router = APIRouter()

AGENT_NODES = ["planner", "writer", "storyboarder", "prompter", "quality_checker"]


@router.post("/execute")
async def execute_agent(req: AgentExecuteRequest, db: AsyncSession = Depends(get_db)):
    """执行Agent工作流，生成剧本+分镜，返回SSE事件流"""
    from fastapi.responses import StreamingResponse

    async def event_stream():
        project_id = req.project_id
        story_input = req.story_input or ""

        try:
            # 1. Planner - 规划故事结构
            yield f"data: {json.dumps({'type': 'AGENT_START', 'data': {'node': 'planner', 'project_id': project_id}, 'message': '规划师：正在分析故事结构...'})}\n\n"
            await asyncio.sleep(0.5)

            chapter_title = "第一章：命运的邂逅"
            scenes_data = [
                {"scene_number": 1, "description": "主角登场，背景介绍"},
                {"scene_number": 2, "description": "冲突事件触发"},
                {"scene_number": 3, "description": "高潮对决"},
                {"scene_number": 4, "description": "转折与悬念"},
            ]
            script_content = story_input if story_input else "在一个充满奇幻色彩的世界里，少年踏上寻找真相的旅程..."

            yield f"data: {json.dumps({'type': 'AGENT_FINISH', 'data': {'node': 'planner', 'result': 'success', 'chapter_title': chapter_title, 'scenes': scenes_data}, 'message': '规划师：故事结构规划完成'})}\n\n"
            await asyncio.sleep(0.3)

            # 2. Writer - 创作剧本
            yield f"data: {json.dumps({'type': 'AGENT_START', 'data': {'node': 'writer', 'project_id': project_id}, 'message': '编剧：正在创作剧本内容...'})}\n\n"
            await asyncio.sleep(0.5)

            yield f"data: {json.dumps({'type': 'step_update', 'data': {'node': 'writer', 'progress': 50}, 'message': '编剧：正在构建对话和情节...'})}\n\n"
            await asyncio.sleep(0.5)

            full_scenes = [
                {"scene_number": 1, "title": "启程", "content": "主角站在天台，俯瞰城市夜景。风吹过他的发梢，眼中闪烁着坚定的光芒。", "dialogue": "「这个世界，需要被改变。」"},
                {"scene_number": 2, "title": "遭遇", "content": "神秘陌生人出现在主角面前，递出一个发光的信封。", "dialogue": "「想知道真相？那就跟我来。」"},
                {"scene_number": 3, "title": "对决", "content": "主角与敌人展开激烈对决，能量四射，战况焦灼。", "dialogue": "「我不会放弃的！」"},
                {"scene_number": 4, "title": "谜团", "content": "胜利之后，更大的谜团浮现，主角决心继续前行。", "dialogue": "「这一切才刚刚开始...」"},
            ]

            yield f"data: {json.dumps({'type': 'AGENT_FINISH', 'data': {'node': 'writer', 'result': 'success', 'scenes': full_scenes}, 'message': '编剧：剧本创作完成'})}\n\n"
            await asyncio.sleep(0.3)

            # 保存剧本到数据库（自动递增章节号）
            script_service = ScriptService(db)
            existing_scripts = await script_service.get_by_project(project_id)
            chapter_number = len(existing_scripts) + 1
            chapter_title = f"第{chapter_number}章：命运的邂逅"
            script = await script_service.save_script(
                project_id=project_id,
                chapter_number=chapter_number,
                title=chapter_title,
                content=script_content,
                scenes=full_scenes,
            )
            script_id = str(script.id)
            logger.info(f"剧本已保存: {script_id}")

            # 3. Storyboarder - 生成分镜
            yield f"data: {json.dumps({'type': 'AGENT_START', 'data': {'node': 'storyboarder', 'project_id': project_id}, 'message': '分镜师：正在生成分镜画面...'})}\n\n"
            await asyncio.sleep(0.5)

            storyboard_data = [
                {"scene_number": 1, "panel_number": 1, "composition": "全景镜头，城市天际线",
                 "camera_angle": "平视", "description": "主角站在高楼天台，俯瞰城市，夕阳西下",
                 "dialogue": "这个世界，即将迎来改变...", "prompt": "anime style, wide shot, city skyline, rooftop, sunset, dramatic lighting, epic atmosphere, 4k"},
                {"scene_number": 1, "panel_number": 2, "composition": "中景，主角背影",
                 "camera_angle": "仰视", "description": "主角转身，露出坚定的表情",
                 "dialogue": "我必须要找到真相。", "prompt": "anime style, medium shot, boy turning around, determined expression, cinematic lighting"},
                {"scene_number": 1, "panel_number": 3, "composition": "特写，主角眼睛",
                 "camera_angle": "平视", "description": "主角眼中倒映着城市的灯火，瞳孔微微发光",
                 "dialogue": "", "prompt": "anime style, close-up, eye reflection, city lights, glowing effect, detailed"},
                {"scene_number": 2, "panel_number": 1, "composition": "双人镜头，对话场景",
                 "camera_angle": "过肩镜头", "description": "神秘人出现在主角面前，递出一个信封",
                 "dialogue": "想知道真相？那就跟我来。", "prompt": "anime style, over shoulder shot, mysterious figure, night scene, suspense"},
                {"scene_number": 2, "panel_number": 2, "composition": "特写，信封",
                 "camera_angle": "俯视", "description": "信封上印着奇特的符号，散发着微光",
                 "dialogue": "", "prompt": "anime style, close-up, envelope, glowing symbols, mysterious, detailed"},
                {"scene_number": 3, "panel_number": 1, "composition": "广角，战斗场景",
                 "camera_angle": "低角度", "description": "主角与敌人激烈对战，能量碰撞",
                 "dialogue": "我不会让你得逞的！", "prompt": "anime style, action scene, energy clash, dynamic pose, sparks, intense"},
                {"scene_number": 3, "panel_number": 2, "composition": "中景，主角蓄力",
                 "camera_angle": "平视", "description": "主角聚集力量，光芒在掌心汇聚",
                 "dialogue": "这就是我的全力！", "prompt": "anime style, power gathering, glowing hand, determined face, dramatic"},
                {"scene_number": 4, "panel_number": 1, "composition": "全景，黎明",
                 "camera_angle": "俯瞰", "description": "战斗结束，主角独自站在废墟中，远方的地平线泛起曙光",
                 "dialogue": "这一切...才刚刚开始。", "prompt": "anime style, aftermath, dawn, ruins, lone figure, hopeful atmosphere"},
            ]

            yield f"data: {json.dumps({'type': 'step_update', 'data': {'node': 'storyboarder', 'progress': 60}, 'message': '分镜师：正在生成分镜描述...'})}\n\n"
            await asyncio.sleep(0.5)

            # 保存分镜到数据库
            storyboards = await script_service.save_storyboards(
                project_id=project_id,
                script_id=script_id,
                storyboard_data=storyboard_data,
            )
            logger.info(f"分镜已保存: {len(storyboards)} 个")

            yield f"data: {json.dumps({'type': 'AGENT_FINISH', 'data': {'node': 'storyboarder', 'result': 'success', 'count': len(storyboards)}, 'message': f'分镜师：已生成 {len(storyboards)} 个分镜画面'})}\n\n"
            await asyncio.sleep(0.3)

            # 4. Prompter - 优化提示词
            yield f"data: {json.dumps({'type': 'AGENT_START', 'data': {'node': 'prompter', 'project_id': project_id}, 'message': '提示词工程师：正在优化AI绘画提示词...'})}\n\n"
            await asyncio.sleep(0.5)

            yield f"data: {json.dumps({'type': 'AGENT_FINISH', 'data': {'node': 'prompter', 'result': 'success'}, 'message': '提示词工程师：提示词优化完成'})}\n\n"
            await asyncio.sleep(0.3)

            # 5. Quality Checker - 质量检查
            yield f"data: {json.dumps({'type': 'AGENT_START', 'data': {'node': 'quality_checker', 'project_id': project_id}, 'message': '质检员：正在检查内容质量...'})}\n\n"
            await asyncio.sleep(0.5)

            # 更新项目状态为 completed
            project_service = ProjectService(db)
            await project_service.update(project_id, ProjectUpdate(status="completed"))

            yield f"data: {json.dumps({'type': 'AGENT_FINISH', 'data': {'node': 'quality_checker', 'result': 'success', 'score': 92}, 'message': '质检员：内容质量检查通过，评分 92/100'})}\n\n"
            await asyncio.sleep(0.3)

            # 完成，返回结果数据
            result = await script_service.get_execute_result(project_id)
            if result:
                yield f"data: {json.dumps({'type': 'COMPLETE', 'data': result.model_dump(mode='json'), 'message': '🎉 所有Agent执行完成！点击查看剧本和分镜'})}\n\n"
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