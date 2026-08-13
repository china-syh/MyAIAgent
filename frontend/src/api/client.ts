import axios from 'axios';
import { getToken } from '../utils/token';

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

http.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (res) => res.data,
  (error) => {
    const msg = error.response?.data?.message || error.message || '请求失败';
    return Promise.reject(new Error(msg));
  }
);

export const projectApi = {
  list: () => http.get('/projects').then(r => r.data),
  get: (id: string) => http.get(`/projects/${id}`).then(r => r.data),
  create: (data: any) => http.post('/projects', data).then(r => r.data),
  update: (id: string, data: any) => http.put(`/projects/${id}`, data).then(r => r.data),
  delete: (id: string) => http.delete(`/projects/${id}`).then(r => r.data),
};

export const agentApi = {
  execute: (data: { project_id: string; story_input?: string }) =>
    http.post('/agents/execute', data).then(r => r.data),
};

export const productionApi = {
  start: (projectId: string, data: { story_input?: string; genre?: string; stages?: string[] }) =>
    http.post(`/production/${projectId}/runs`, data).then(r => r.data),
  get: (runId: string) => http.get(`/production/runs/${runId}`).then(r => r.data),
  pause: (runId: string) => http.post(`/production/runs/${runId}/pause`).then(r => r.data),
  resume: (runId: string) => http.post(`/production/runs/${runId}/resume`).then(r => r.data),
  retryStage: (runId: string, stage: string) => http.post(`/production/runs/${runId}/stages/${stage}/retry`).then(r => r.data),
};

export const healthApi = {
  check: () => http.get('/health').then(r => r.data),
};

export const scriptApi = {
  list: (projectId: string) => http.get(`/projects/${projectId}/scripts`).then(r => r.data),
  latest: (projectId: string) => http.get(`/projects/${projectId}/scripts/latest`).then(r => r.data),
  storyboards: (projectId: string) => http.get(`/projects/${projectId}/storyboards`).then(r => r.data),
  executeResult: (projectId: string) => http.get(`/projects/${projectId}/execute-result`).then(r => r.data),
  deleteScript: (projectId: string, scriptId: string) => http.delete(`/projects/${projectId}/scripts/${scriptId}`).then(r => r.data),
};

export const dashboardApi = {
  stats: () => http.get('/dashboard/stats').then(r => r.data),
};

export const taskApi = {
  list: (projectId?: string) =>
    http.get('/tasks', { params: { project_id: projectId } }).then(r => r.data),
  get: (id: string) => http.get(`/tasks/${id}`).then(r => r.data),
  cancel: (id: string) => http.post(`/tasks/${id}/cancel`).then(r => r.data),
  generateImage: (data: { project_id: string; storyboard_id: string; prompt: string }) =>
    http.post('/tasks/generate-image', data).then(r => r.data),
  composeVideo: (data: { project_id: string; episode_id: string }) =>
    http.post('/tasks/compose-video', data).then(r => r.data),
  getPending: () =>
    http.get('/tasks/pending/generation').then(r => r.data),
  submitResult: (taskId: string, result: Record<string, unknown>) =>
    http.post(`/tasks/${taskId}/submit-generation`, { result }).then(r => r.data),
};

export const assetApi = {
  episodes: {
    list: (projectId: string) => http.get(`/assets/${projectId}/episodes`).then(r => r.data),
    create: (projectId: string, data: any) => http.post(`/assets/${projectId}/episodes`, data).then(r => r.data),
    update: (projectId: string, id: string, data: any) => http.put(`/assets/${projectId}/episodes/${id}`, data).then(r => r.data),
  },
  scenes: {
    list: (projectId: string) => http.get(`/assets/${projectId}/scenes`).then(r => r.data),
    create: (projectId: string, data: any) => http.post(`/assets/${projectId}/scenes`, data).then(r => r.data),
  },
  props: {
    list: (projectId: string) => http.get(`/assets/${projectId}/props`).then(r => r.data),
    create: (projectId: string, data: any) => http.post(`/assets/${projectId}/props`, data).then(r => r.data),
  },
  voices: {
    list: (projectId: string) => http.get(`/assets/${projectId}/voices`).then(r => r.data),
    create: (projectId: string, data: any) => http.post(`/assets/${projectId}/voices`, data).then(r => r.data),
  },
};

export const authApi = {
  login: (data: { username: string; password: string }) =>
    http.post('/auth/login', data).then(r => r.data),
  register: (data: { username: string; email: string; password: string; display_name?: string }) =>
    http.post('/auth/register', data).then(r => r.data),
  getMe: () => http.get('/auth/me').then(r => r.data),
};

// ===== 小说解析 =====
export const novelApi = {
  parse: (data: { project_id: string; story_input?: string }) =>
    http.post('/novel/parse', data).then(r => r.data),
  analyze: (data: { project_id: string; story_input?: string }) =>
    http.post('/novel/analyze', data).then(r => r.data),
};

// ===== 角色 =====
export const characterApi = {
  list: (projectId: string) => http.get(`/projects/${projectId}/characters`).then(r => r.data),
};

// ===== 故事图谱 =====
export const storyGraphApi = {
  list: (projectId: string) => http.get(`/story-graph/${projectId}`).then(r => r.data),
  create: (projectId: string, data: any) => http.post(`/story-graph/${projectId}`, data).then(r => r.data),
  delete: (projectId: string, id: string) => http.delete(`/story-graph/${projectId}/${id}`).then(r => r.data),
};

// ===== 自由画布 =====
export const freezoneApi = {
  list: (projectId: string) => http.get(`/freezone/${projectId}`).then(r => r.data),
  create: (projectId: string, data: any) => http.post(`/freezone/${projectId}`, data).then(r => r.data),
  update: (projectId: string, nodeId: string, data: any) => http.put(`/freezone/${projectId}/${nodeId}`, data).then(r => r.data),
  delete: (projectId: string, nodeId: string) => http.delete(`/freezone/${projectId}/${nodeId}`).then(r => r.data),
};

// ===== 导演世界 =====
export const directorWorldApi = {
  list: (projectId: string) => http.get(`/director-world/${projectId}`).then(r => r.data),
  create: (projectId: string, data: any) => http.post(`/director-world/${projectId}`, data).then(r => r.data),
  delete: (projectId: string, worldId: string) => http.delete(`/director-world/${projectId}/${worldId}`).then(r => r.data),
};

// ===== AI助手 =====
export const aiAssistantApi = {
  getChat: (projectId: string) => http.get(`/ai-assistant/chat/${projectId}`).then(r => r.data),
  sendMessage: (data: { project_id?: string; content: string; message_type?: string }) =>
    http.post('/ai-assistant/chat', data).then(r => r.data),
  sendMessageWithProject: (projectId: string, data: { content: string }) =>
    http.post(`/ai-assistant/chat/${projectId}`, data).then(r => r.data),
};

// ===== 风格模板 =====
export const styleTemplateApi = {
  list: (projectId?: string) => http.get('/style-templates', { params: { project_id: projectId } }).then(r => r.data),
  create: (data: any) => http.post('/style-templates', data).then(r => r.data),
  apply: (templateId: string, data: { project_id: string }) => http.post(`/style-templates/${templateId}/apply`, data).then(r => r.data),
  delete: (templateId: string) => http.delete(`/style-templates/${templateId}`).then(r => r.data),
};

export default http;
