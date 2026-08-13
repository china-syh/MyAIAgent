import { create } from 'zustand';
import { projectApi } from '../api/client';
import type { Project } from '../types';

interface ProjectState {
  projects: Project[];
  loading: boolean;
  fetchProjects: () => Promise<void>;
  createProject: (data: any) => Promise<any>;
  deleteProject: (id: string) => Promise<void>;
}

export const useProjectStore = create<ProjectState>((set) => ({
  projects: [],
  loading: false,
  fetchProjects: async () => {
    set({ loading: true });
    try {
      const res = await projectApi.list();
      set({ projects: Array.isArray(res) ? res : [] });
    } finally {
      set({ loading: false });
    }
  },
  createProject: async (data) => {
    const res = await projectApi.create(data);
    const project = res;
    set((s) => ({ projects: [project, ...s.projects] }));
    return project;
  },
  deleteProject: async (id) => {
    await projectApi.delete(id);
    set((s) => ({ projects: s.projects.filter((p) => p.id !== id) }));
  },
}));