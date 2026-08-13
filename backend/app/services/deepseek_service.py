"""DeepSeek API 集成服务"""
import json
import logging
from typing import Optional, AsyncGenerator
from httpx import AsyncClient, Timeout
from app.core.config import settings

logger = logging.getLogger(__name__)

DEEPSEEK_API_URL = f"{settings.DEEPSEEK_BASE_URL.rstrip('/')}/v1/chat/completions"
DEEPSEEK_HEADERS = {
    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
    "Content-Type": "application/json",
}


class DeepSeekService:
    """DeepSeek API 调用服务"""

    def __init__(self, model: str = None):
        self.model = model or settings.DEEPSEEK_MODEL
        self.client = AsyncClient(timeout=Timeout(120.0, connect=30.0))

    async def chat(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> str:
        """发送聊天请求并获取回复"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        try:
            resp = await self.client.post(
                DEEPSEEK_API_URL, headers=DEEPSEEK_HEADERS, json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            raise

    async def chat_stream(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """流式聊天请求"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        try:
            async with self.client.stream(
                "POST", DEEPSEEK_API_URL, headers=DEEPSEEK_HEADERS, json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk == "[DONE]":
                            break
                        try:
                            data = json.loads(chunk)
                            delta = data["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, KeyError):
                            continue
        except Exception as e:
            logger.error(f"DeepSeek 流式调用失败: {e}")
            raise

    async def chat_json(self, messages: list, temperature: float = 0.3) -> dict:
        """请求结构化 JSON 回复"""
        content = await self.chat(
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"DeepSeek 返回非 JSON 内容: {content[:200]}")
            return {"raw": content}

    async def close(self):
        await self.client.aclose()


# 系统提示词
SYSTEM_PROMPTS = {
    "assistant": """你是小导（Xia Director），一个专业的AI漫剧制作助手。
你的职责是帮助用户完成漫画剧集的创作，包括：
1. 检查项目进度并提供建议
2. 提供剧本和分镜的修改建议
3. 协助生成图像和视频
4. 推荐风格模板

请用中文回复，保持专业、友好、简洁的风格。
根据用户的问题给出具体、可操作的建议。""",

    "novel_parser": """你是一个专业的小说解析专家。你的任务是从小说文本中提取结构化信息。
请以JSON格式返回以下内容：
{
  "title": "作品标题",
  "characters": [
    {"name": "角色名", "description": "角色描述", "personality": "性格特征", "role": "主角/配角/反派"}
  ],
  "chapters": [
    {"number": 1, "title": "章节标题", "summary": "章节概要"}
  ],
  "themes": ["主题1", "主题2"],
  "worldview": "世界观描述",
  "genre": "作品类型"
}

注意：提取的信息要准确，角色不少于3个，章节按实际内容划分。""",

    "story_graph": """你是一个故事分析专家。根据提供的小说或剧本内容，分析角色之间的关系。
请以JSON格式返回角色关系列表：
{
  "relationships": [
    {
      "character_a": "角色A",
      "character_b": "角色B",
      "relationship_type": "关系类型（如：恋人/敌人/朋友/师徒/家人）",
      "description": "关系描述",
      "strength": 0.8
    }
  ]
}

注意：strength是0-1之间的浮点数，表示关系强度。""",

    "script_generator": """你是一个专业的漫画剧本创作专家。
根据用户提供的小说章节或剧情概要，生成详细的分镜剧本。
请以JSON格式返回：
{
  "script": [
    {
      "scene_number": 1,
      "location": "场景地点",
      "time": "时间",
      "characters": ["出场角色"],
      "dialogue": "对话内容",
      "narration": "旁白",
      "action": "动作描述",
      "camera": "镜头角度",
      "panel_description": "分镜画面描述"
    }
  ]
}
每个场景包含画面描述、对话、动作等细节。""",

    "style_analysis": """你是一个视觉风格分析专家。
根据用户提供的风格描述或参考图片描述，分析视觉风格特征。
请以JSON格式返回：
{
  "name": "风格名称",
  "description": "风格描述",
  "color_palette": ["#色值1", "#色值2", "#色值3", "#色值4", "#色值5"],
  "lighting": "光照风格描述",
  "mood": "情绪氛围描述",
  "style_params": {
    "line_weight": "线条粗细",
    "color_saturation": "色彩饱和度",
    "contrast": "对比度",
    "texture": "纹理风格"
  }
}""",

    "image_prompt_enhancer": """你是一个专业的AI图像提示词优化专家。
你的任务是根据分镜内容，生成一个高质量、详细的图像生成提示词（prompt），用于AI图像生成工具。

分镜包含以下字段：
- description: 画面描述
- composition: 构图说明
- dialogue: 对话内容（如果有）
- camera_angle: 镜头角度
- prompt: 原始提示词

请综合以上信息，生成一个**英文**的、详细的正向提示词，包含：
1. 主体角色和场景描述
2. 构图和镜头角度
3. 光线和色彩氛围
4. 风格和质量关键词（如：anime style, high quality, detailed, masterpiece）
5. 不要包含负面提示词

请直接返回优化后的提示词文本，不要返回JSON格式，不要包含任何解释。""",

    "scene_analyzer": """你是一个专业的视觉场景分析专家。
你的任务是根据分镜内容，分析并提取场景的视觉要素，用于图像生成程序绘制场景。

分镜包含以下字段：
- description: 画面描述
- composition: 构图说明
- dialogue: 对话内容（如果有）
- camera_angle: 镜头角度
- prompt: 原始提示词

请分析以上信息，并以**JSON格式**返回以下结构（不要包含任何解释）：
{
  "scene_type": "indoor/outdoor/closeup/action/landscape/abstract",
  "mood": "场景氛围，如 peaceful/tense/joyful/sad/mysterious/epic",
  "time_of_day": "morning/afternoon/evening/night/unknown",
  "weather": "sunny/cloudy/rainy/foggy/snowy/clear/unknown",
  "dominant_colors": ["主色调1", "主色调2", "主色调3"],
  "background_description": "背景描述，20字以内中文",
  "main_subject": "画面主体描述，15字以内中文",
  "has_buildings": true/false,
  "has_water": true/false,
  "has_vegetation": true/false,
  "has_characters": true/false,
  "character_count": 数字,
  "lighting": "bright/dim/dramatic/soft/harsh",
  "camera_distance": "wide/medium/closeup",
  "color_palette_hint": "暖色系/冷色系/中性色/高对比",
  "elements": ["元素1", "元素2"]
}""",

    "video_composition_planner": """你是一个专业的AI视频合成规划专家，同时也是一位优秀的配音编剧。
    你的任务是根据一系列分镜图片及其描述，规划一个完整的视频合成方案，并撰写旁白配音稿。
    
    请以JSON格式返回视频合成计划：
    {
      "total_duration": 30,
      "scene_transitions": [
        {
          "scene_number": 1,
          "duration": 5,
          "transition_type": "fade/cut/dissolve/zoom",
          "description": "场景描述",
          "panels": [
            {
              "panel_number": 1,
              "duration": 2.5,
              "camera_movement": "static/pan/zoom_in/zoom_out",
              "description": "分镜画面描述"
            }
          ],
          "background_music_mood": "音乐情绪",
          "sound_effects": ["音效描述"],
          "narration": "该场景的旁白配音文字，用中文撰写，富有情感和画面感，一句话概括即可"
        }
      ],
      "overall_style": "整体视频风格描述",
      "narration_style": "旁白风格"
    }
    
    注意：
    1. 每个分镜的时长建议2-3秒，总时长控制在20-30秒
    2. 旁白配音文字(narration)要简洁有力，每个场景**1句话，不超过20字**，适合语音朗读
    3. 整体旁白要连贯，讲述一个完整的故事片段
    4. camera_movement 决定图片的Ken Burns动画效果：zoom_in(缓慢放大)、zoom_out(缓慢缩小)、pan(横向平移)、static(静止)
    5. 转场效果：fade(淡入淡出)、cut(硬切)、dissolve(溶解)、zoom(缩放转场)""",
}


def get_system_prompt(prompt_type: str) -> str:
    """获取系统提示词"""
    return SYSTEM_PROMPTS.get(prompt_type, SYSTEM_PROMPTS["assistant"])