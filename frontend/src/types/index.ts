// ============ 项目类型 ============

export interface Character {
  id: string;
  project_id: string;
  name: string;
  role: string;
  age: string;
  gender: string;
  personality: string;
  appearance: string;
  background: string;
  created_at: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  genre: string;
  status: 'draft' | 'generating' | 'completed' | 'failed';
  world_setting: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  characters: Character[];
}

export interface ProjectCreate {
  name: string;
  description?: string;
  genre?: string;
  story_input?: string;
}

// ============ Agent 事件类型 ============

export interface AgentEvent {
  type: 'AGENT_START' | 'AGENT_FINISH' | 'STEP_START' | 'STEP_UPDATE' | 'TOOL_CALL' | 'INTERRUPT' | 'ERROR';
  node?: string;
  data?: Record<string, unknown>;
  message: string;
}

export interface AgentState {
  status: 'idle' | 'running' | 'done' | 'error';
  events: AgentEvent[];
  currentAgent: string;
  progress: number;
}

// ============ 分镜/提示词类型 ============

export interface Storyboard {
  id?: string;
  script_id?: string;
  scene_number: number;
  panel_number: number;
  composition: string;
  camera_angle: string;
  description: string;
  dialogue: string;
  prompt?: string;
  image_url?: string;
}

export interface Script {
  id: string;
  project_id: string;
  chapter_number: number;
  title: string;
  content: string;
  scenes: any[];
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Prompt {
  panel_number: number;
  positive_prompt: string;
  negative_prompt: string;
  style_params?: Record<string, unknown>;
}

// ============ API 响应 ============

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface HealthStatus {
  status: string;
  app: string;
  version: string;
}

// ============ 任务中心 ============

export interface TaskItem {
  id: string;
  project_id: string | null;
  name: string;
  type: 'image_gen' | 'voiceover' | 'video_compose' | 'script' | 'storyboard' | 'asset';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  total_steps: number;
  current_step: number;
  result: Record<string, unknown>;
  error: string;
  logs: Array<{ time: string; message: string }>;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

// ============ 剧集规划 ============

export interface Episode {
  id: string;
  project_id: string;
  episode_number: number;
  title: string;
  summary: string;
  beats: Array<{ beat_number: number; description: string; duration: string }>;
  status: string;
  order: number;
  created_at: string;
  updated_at: string;
}

// ============ 场景 ============

export interface Scene {
  id: string;
  project_id: string;
  name: string;
  description: string;
  atmosphere: string;
  time_of_day: string;
  reference_image: string;
  style_params: Record<string, unknown>;
  created_at: string;
}

// ============ 道具 ============

export interface Prop {
  id: string;
  project_id: string;
  name: string;
  category: string;
  description: string;
  reference_image: string;
  created_at: string;
}

// ============ 配音 ============

export interface Voice {
  id: string;
  project_id: string;
  character_name: string;
  gender: string;
  style: string;
  pitch: number;
  speed: number;
  sample_url: string;
  status: string;
  created_at: string;
}

// ============ 故事图谱 ============

export interface StoryRelation {
  id: string;
  project_id: string;
  character_a_id: string;
  character_b_id: string;
  relationship_type: string;
  description: string;
  strength: number;
  created_at: string;
}

// ============ 自由画布 ============

export interface FreezoneNode {
  id: string;
  project_id: string;
  parent_id: string | null;
  type: 'image' | 'video' | 'audio' | 'text' | 'storyboard' | 'script';
  title: string;
  content: Record<string, unknown>;
  position_x: number;
  position_y: number;
  width: number;
  height: number;
  color: string;
  tags: string[];
  status: string;
  order: number;
  created_at: string;
  updated_at: string;
}

// ============ 导演世界 ============

export interface DirectorWorld {
  id: string;
  project_id: string;
  scene_id: string | null;
  name: string;
  description: string;
  camera_position: Record<string, unknown>;
  character_blocking: Array<Record<string, unknown>>;
  spatial_layout: Record<string, unknown>;
  variants: Array<Record<string, unknown>>;
  thumbnail: string;
  status: string;
  created_at: string;
  updated_at: string;
}

// ============ AI助手 ============

export interface AIChatMessage {
  id: string;
  project_id: string | null;
  user_id: string | null;
  role: 'user' | 'assistant';
  content: string;
  message_type: 'text' | 'suggestion' | 'audit' | 'action';
  metadata: Record<string, unknown>;
  created_at: string;
}

// ============ 风格模板 ============

export interface StyleTemplate {
  id: string;
  project_id: string | null;
  name: string;
  description: string;
  reference_image: string;
  style_params: Record<string, unknown>;
  color_palette: string[];
  lighting: string;
  mood: string;
  is_global: boolean;
  created_at: string;
  updated_at: string;
}