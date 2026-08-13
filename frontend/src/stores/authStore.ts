import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi } from '../api/auth';
import type { User, LoginRequest } from '../types/auth';

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (data: LoginRequest) => Promise<void>;
  register: (data: { username: string; email: string; password: string; display_name?: string }) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      isAuthenticated: false,

      login: async (data) => {
        const res = await authApi.login(data);
        const token = res.data?.access_token || res.access_token;
        set({ token, isAuthenticated: true });
        try { await get().fetchUser(); } catch {}
      },

      register: async (data) => {
        const res = await authApi.register(data);
        const token = res.data?.access_token || res.access_token;
        set({ token, isAuthenticated: true });
      },

      logout: () => {
        set({ token: null, user: null, isAuthenticated: false });
        localStorage.removeItem('manga-auth-storage');
      },

      fetchUser: async () => {
        const res = await authApi.getMe();
        set({ user: res.data || res });
      },
    }),
    {
      name: 'manga-auth-storage',
      partialize: (state) => ({ token: state.token, isAuthenticated: state.isAuthenticated }),
      onRehydrateStorage: () => {
        return (state) => {
          // 重新水合后，如果有 token 则尝试获取用户信息
          if (state?.token) {
            state.fetchUser().catch(() => {
              // token 过期或无效，清除状态
              state.logout();
            });
          }
        };
      },
    }
  )
);