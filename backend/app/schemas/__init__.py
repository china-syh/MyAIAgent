from pydantic import BaseModel, Field
from typing import TypeVar, Generic, List, Optional, Any
from uuid import UUID
from datetime import datetime

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: Optional[T] = None


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PageResult(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int = 0

    def __init__(self, **data):
        super().__init__(**data)
        self.total_pages = (self.total + self.page_size - 1) // self.page_size if self.page_size > 0 else 0


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    story_input: str = ""
    genre: str = "fantasy"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    story_input: Optional[str] = None
    genre: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str
    story_input: str
    genre: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CharacterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: str = ""
    age: str = ""
    gender: str = ""
    personality: str = ""
    appearance: str = ""
    background: str = ""


class CharacterResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    role: str
    age: str
    gender: str
    personality: str
    appearance: str
    background: str
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    email: str = Field(..., max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    display_name: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    display_name: str
    avatar_url: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class AgentExecuteRequest(BaseModel):
    project_id: str
    story_input: str = ""


class ScriptResponse(BaseModel):
    id: UUID
    project_id: UUID
    chapter_number: int
    title: str
    content: str
    scenes: list
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StoryboardResponse(BaseModel):
    id: UUID
    project_id: UUID
    script_id: Optional[UUID] = None
    scene_number: int
    panel_number: int
    description: str
    composition: str
    dialogue: str
    camera_angle: str
    prompt: str
    image_url: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ExecuteResultResponse(BaseModel):
    project_id: UUID
    scripts: List[ScriptResponse] = []
    storyboards: List[StoryboardResponse] = []


# ===== Task =====
class TaskResponse(BaseModel):
    id: UUID
    project_id: Optional[UUID] = None
    name: str
    type: str
    status: str
    progress: int
    total_steps: int
    current_step: int
    result: dict
    error: str
    logs: list
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True


class ProductionRunCreate(BaseModel):
    story_input: str = ""
    genre: str = "fantasy"
    stages: list[str] = []


class ProductionStageResponse(BaseModel):
    id: UUID
    run_id: UUID
    name: str
    order: int
    status: str
    input_data: dict
    output_data: dict
    error: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config: from_attributes = True


class ProductionRunResponse(BaseModel):
    id: UUID
    project_id: UUID
    status: str
    current_stage: str
    input_snapshot: dict
    output: dict
    error: str
    created_at: datetime
    updated_at: datetime
    stages: list[ProductionStageResponse] = []

    class Config: from_attributes = True

# ===== Episode =====
class EpisodeCreate(BaseModel):
    episode_number: int = 1
    title: str = ""
    summary: str = ""
    beats: list = []
class EpisodeUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    beats: Optional[list] = None
    status: Optional[str] = None
class EpisodeResponse(BaseModel):
    id: UUID
    project_id: UUID
    episode_number: int
    title: str
    summary: str
    beats: list
    status: str
    order: int
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True

# ===== Scene =====
class SceneCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    atmosphere: str = ""
    time_of_day: str = "day"
    reference_image: str = ""
    style_params: dict = {}
class SceneResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    description: str
    atmosphere: str
    time_of_day: str
    reference_image: str
    style_params: dict
    created_at: datetime
    class Config: from_attributes = True

# ===== Prop =====
class PropCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = "prop"
    description: str = ""
    reference_image: str = ""
class PropResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    category: str
    description: str
    reference_image: str
    created_at: datetime
    class Config: from_attributes = True

# ===== Voice =====
class VoiceCreate(BaseModel):
    character_name: str = Field(..., min_length=1, max_length=100)
    gender: str = "neutral"
    style: str = "natural"
    pitch: float = 1.0
    speed: float = 1.0
    sample_url: str = ""
class VoiceResponse(BaseModel):
    id: UUID
    project_id: UUID
    character_name: str
    gender: str
    style: str
    pitch: float
    speed: float
    sample_url: str
    status: str
    created_at: datetime
    class Config: from_attributes = True

# ===== Image Generation =====
class ImageGenRequest(BaseModel):
    project_id: str
    storyboard_id: str
    prompt: str = ""
    negative_prompt: str = ""
    style: str = "anime"
class ImageGenResponse(BaseModel):
    task_id: UUID
    image_url: str = ""
    status: str = "processing"

# ===== Video Compose =====
class VideoComposeRequest(BaseModel):
    project_id: str
    episode_id: str = ""
    include_voiceover: bool = True
    resolution: str = "1920x1080"


class DashboardStats(BaseModel):
    total_projects: int = 0
    completed: int = 0
    generating: int = 0
    failed: int = 0
    draft: int = 0


# ===== 故事图谱 =====
class CharacterRelationshipCreate(BaseModel):
    character_a_id: str = ""
    character_b_id: str = ""
    relationship_type: str = ""
    description: str = ""
    strength: int = 5
class CharacterRelationshipResponse(BaseModel):
    id: UUID
    project_id: UUID
    character_a_id: UUID
    character_b_id: UUID
    relationship_type: str
    description: str
    strength: int
    created_at: datetime
    class Config: from_attributes = True

# ===== 自由画布 =====
class FreezoneNodeCreate(BaseModel):
    type: str = "text"
    title: str = ""
    content: str = ""
    position_x: float = 0
    position_y: float = 0
    width: float = 200
    height: float = 200
    color: str = "#7c3aed"
    tags: list = []
    parent_id: Optional[str] = None
class FreezoneNodeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    color: Optional[str] = None
    tags: Optional[list] = None
class FreezoneNodeResponse(BaseModel):
    id: UUID
    project_id: UUID
    parent_id: Optional[UUID] = None
    type: str
    title: str
    content: str
    position_x: float
    position_y: float
    width: float
    height: float
    color: str
    tags: list
    status: str
    order: int
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True

# ===== 导演世界 =====
class DirectorWorldCreate(BaseModel):
    scene_id: Optional[str] = None
    name: str = ""
    description: str = ""
    camera_position: dict = {}
    character_blocking: list = []
    spatial_layout: dict = {}
    variants: list = []
class DirectorWorldResponse(BaseModel):
    id: UUID
    project_id: UUID
    scene_id: Optional[UUID] = None
    name: str
    description: str
    camera_position: dict
    character_blocking: list
    spatial_layout: dict
    variants: list
    thumbnail: str
    status: str
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True

# ===== AI助手 =====
class AIChatCreate(BaseModel):
    project_id: Optional[str] = None
    content: str = ""
    message_type: str = "text"
    meta_data: dict = {}
class AIChatResponse(BaseModel):
    id: UUID
    project_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    role: str
    content: str
    message_type: str
    meta_data: dict = {}
    created_at: datetime
    class Config: from_attributes = True

# ===== 风格模板 =====
class StyleTemplateCreate(BaseModel):
    name: str = ""
    description: str = ""
    reference_image: str = ""
    style_params: dict = {}
    color_palette: list = []
    lighting: str = ""
    mood: str = ""
    is_global: bool = False
class StyleTemplateResponse(BaseModel):
    id: UUID
    project_id: Optional[UUID] = None
    name: str
    description: str
    reference_image: str
    style_params: dict
    color_palette: list
    lighting: str
    mood: str
    is_global: bool
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True
