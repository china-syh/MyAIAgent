import React, { useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { getToken } from '../../utils/token';
import { Spin } from 'antd';

interface AuthGuardProps {
  children: React.ReactNode;
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const storeToken = useAuthStore((state) => state.token);
  const token = getToken();

  // 如果 localStorage 有 token 但 store 恢复失败（token 无效），等 fetchUser 失败后自动跳转登录页
  if (token && !isAuthenticated) {
    // 如果 store 已经尝试过恢复但失败了（token 被清空），直接跳转
    if (!storeToken) {
      localStorage.removeItem('manga-auth-storage');
      return <Navigate to="/login" replace />;
    }
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="恢复登录状态..." />
      </div>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export default AuthGuard;