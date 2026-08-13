import { createBrowserRouter, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import AppLayout from '../components/layout/AppLayout';
import AuthGuard from '../components/layout/AuthGuard';
import PageLoading from '../components/common/PageLoading';

const LoginPage = lazy(() => import('../pages/LoginPage'));
const RegisterPage = lazy(() => import('../pages/RegisterPage'));
const DashboardPage = lazy(() => import('../pages/DashboardPage'));
const ProjectsPage = lazy(() => import('../pages/ProjectsPage'));
const AgentPage = lazy(() => import('../pages/AgentPage'));
const EditorPage = lazy(() => import('../pages/EditorPage'));
const TaskCenterPage = lazy(() => import('../pages/TaskCenterPage'));
const AssetLibraryPage = lazy(() => import('../pages/AssetLibraryPage'));
const NovelParserPage = lazy(() => import('../pages/NovelParserPage'));
const StoryGraphPage = lazy(() => import('../pages/StoryGraphPage'));
const FreezonePage = lazy(() => import('../pages/FreezonePage'));
const DirectorWorldPage = lazy(() => import('../pages/DirectorWorldPage'));
const AIAssistantPage = lazy(() => import('../pages/AIAssistantPage'));
const StyleTemplatesPage = lazy(() => import('../pages/StyleTemplatesPage'));
const ProductionPage = lazy(() => import('../pages/ProductionPage'));

const LazyLoad = ({ children }: { children: React.ReactNode }) => (
  <Suspense fallback={<PageLoading />}>{children}</Suspense>
);

export const router = createBrowserRouter([
  {
    path: '/login',
    element: (
      <LazyLoad>
        <LoginPage />
      </LazyLoad>
    ),
  },
  {
    path: '/register',
    element: (
      <LazyLoad>
        <RegisterPage />
      </LazyLoad>
    ),
  },
  {
    path: '/',
    element: (
      <AuthGuard>
        <AppLayout />
      </AuthGuard>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      {
        path: 'dashboard',
        element: (
          <LazyLoad>
            <DashboardPage />
          </LazyLoad>
        ),
      },
      {
        path: 'projects',
        element: (
          <LazyLoad>
            <ProjectsPage />
          </LazyLoad>
        ),
      },
      {
        path: 'agent',
        element: (
          <LazyLoad>
            <AgentPage />
          </LazyLoad>
        ),
      },
      {
        path: 'editor',
        element: (
          <LazyLoad>
            <EditorPage />
          </LazyLoad>
        ),
      },
      {
        path: 'tasks',
        element: (
          <LazyLoad>
            <TaskCenterPage />
          </LazyLoad>
        ),
      },
      {
        path: 'assets',
        element: (
          <LazyLoad>
            <AssetLibraryPage />
          </LazyLoad>
        ),
      },
      {
        path: 'novel',
        element: (
          <LazyLoad>
            <NovelParserPage />
          </LazyLoad>
        ),
      },
      {
        path: 'story-graph',
        element: (
          <LazyLoad>
            <StoryGraphPage />
          </LazyLoad>
        ),
      },
      {
        path: 'freezone',
        element: (
          <LazyLoad>
            <FreezonePage />
          </LazyLoad>
        ),
      },
      {
        path: 'director-world',
        element: (
          <LazyLoad>
            <DirectorWorldPage />
          </LazyLoad>
        ),
      },
      {
        path: 'ai-assistant',
        element: (
          <LazyLoad>
            <AIAssistantPage />
          </LazyLoad>
        ),
      },
      {
        path: 'style-templates',
        element: (
          <LazyLoad>
            <StyleTemplatesPage />
          </LazyLoad>
        ),
      },
      { path: 'production', element: <LazyLoad><ProductionPage /></LazyLoad> },
    ],
  },
]);
