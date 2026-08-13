from enum import Enum


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentNode(str, Enum):
    PLANNER = "planner"
    WRITER = "writer"
    STORYBOARDER = "storyboarder"
    PROMPTER = "prompter"
    QUALITY_CHECKER = "quality_checker"


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"