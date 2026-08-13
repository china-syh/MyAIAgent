from fastapi import APIRouter
from app.api.v1 import auth, projects, agents, dashboard, upload, scripts, tasks, assets
from app.api.v1 import novel, story_graph, freezone, director_world, ai_assistant, style_templates, production

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_v1_router.include_router(projects.router, prefix="/projects", tags=["项目"])
api_v1_router.include_router(scripts.router, prefix="/projects", tags=["项目内容"])
api_v1_router.include_router(agents.router, prefix="/agents", tags=["Agent"])
api_v1_router.include_router(tasks.router, prefix="/tasks", tags=["任务中心"])
api_v1_router.include_router(assets.router, prefix="/assets", tags=["资产库"])
api_v1_router.include_router(dashboard.router, prefix="/dashboard", tags=["仪表盘"])
api_v1_router.include_router(upload.router, prefix="/upload", tags=["文件上传"])
api_v1_router.include_router(novel.router, prefix="/novel", tags=["小说解析"])
api_v1_router.include_router(story_graph.router, prefix="/story-graph", tags=["故事图谱"])
api_v1_router.include_router(freezone.router, prefix="/freezone", tags=["自由画布"])
api_v1_router.include_router(director_world.router, prefix="/director-world", tags=["导演世界"])
api_v1_router.include_router(ai_assistant.router, prefix="/ai-assistant", tags=["AI助手"])
api_v1_router.include_router(style_templates.router, prefix="/style-templates", tags=["风格模板"])
api_v1_router.include_router(production.router, prefix="/production", tags=["production"])
