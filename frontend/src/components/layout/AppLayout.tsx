import React from 'react';
import { Layout, Menu, Typography, Space } from 'antd';
import {
  DashboardOutlined,
  ProjectOutlined,
  RobotOutlined,
  EditOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  ExperimentOutlined,
  TeamOutlined,
  FileTextOutlined,
  ShareAltOutlined,
  AppstoreOutlined,
  CameraOutlined,
  MessageOutlined,
  BgColorsOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useUIStore } from '../../stores/uiStore';
import { useAuthStore } from '../../stores/authStore';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '工作台' },
  { key: '/projects', icon: <ProjectOutlined />, label: '项目管理' },
  { key: '/agent', icon: <RobotOutlined />, label: 'Agent 监控' },
  { key: '/editor', icon: <EditOutlined />, label: '分镜编辑器' },
  { key: '/novel', icon: <FileTextOutlined />, label: '小说解析' },
  { key: '/story-graph', icon: <ShareAltOutlined />, label: '故事图谱' },
  { key: '/freezone', icon: <AppstoreOutlined />, label: '自由创作' },
  { key: '/director-world', icon: <CameraOutlined />, label: '导演世界' },
  { key: '/ai-assistant', icon: <MessageOutlined />, label: 'AI 助手' },
  { key: '/style-templates', icon: <BgColorsOutlined />, label: '风格模板' },
  { key: '/tasks', icon: <ExperimentOutlined />, label: '任务中心' },
  { key: '/assets', icon: <TeamOutlined />, label: '资源库' },
];

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const user = useAuthStore((state) => state.user);

  // 计算当前选中菜单项（支持子路径）
  const selectedKey = '/' + location.pathname.split('/')[1];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={240}
        theme="dark"
        collapsible
        collapsed={sidebarCollapsed}
        onCollapse={toggleSidebar}
        trigger={null}
        style={{
          background: 'linear-gradient(180deg, #1e1b4b 0%, #0f0d2e 100%)',
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <Text
            strong
            style={{
              color: '#fff',
              fontSize: sidebarCollapsed ? 14 : 18,
              margin: 0,
            }}
          >
            {sidebarCollapsed ? 'AI' : 'AI 漫剧 Agent'}
          </Text>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{
            background: 'transparent',
            borderRight: 0,
          }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            borderBottom: '1px solid #f0f0f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Space>
            {React.createElement(
              sidebarCollapsed ? MenuUnfoldOutlined : MenuFoldOutlined,
              {
                onClick: toggleSidebar,
                style: { fontSize: 18, cursor: 'pointer' },
              }
            )}
            <Text strong style={{ fontSize: 16, color: '#666' }}>
              AI 漫剧 Agent
            </Text>
          </Space>
          <Space>
            <UserOutlined />
            <Text>{user?.display_name || '用户'}</Text>
          </Space>
        </Header>
        <Content style={{ margin: 24, minHeight: 280 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;