import React from 'react';
import { Row, Col, Card, Statistic, Typography } from 'antd';
import {
  ProjectOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../stores/authStore';

const { Title } = Typography;

const DashboardPage: React.FC = () => {
  const user = useAuthStore((state) => state.user);

  const stats = [
    {
      title: '总项目数',
      value: 12,
      icon: <ProjectOutlined style={{ fontSize: 24, color: '#7c3aed' }} />,
      color: '#7c3aed',
    },
    {
      title: '已完成',
      value: 8,
      icon: <CheckCircleOutlined style={{ fontSize: 24, color: '#52c41a' }} />,
      color: '#52c41a',
    },
    {
      title: '生成中',
      value: 3,
      icon: <SyncOutlined style={{ fontSize: 24, color: '#1890ff' }} />,
      color: '#1890ff',
    },
    {
      title: '失败',
      value: 1,
      icon: <CloseCircleOutlined style={{ fontSize: 24, color: '#ff4d4f' }} />,
      color: '#ff4d4f',
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>
        欢迎回来，{user?.display_name || '用户'}
      </Title>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {stats.map((stat) => (
          <Col xs={24} sm={12} lg={6} key={stat.title}>
            <Card hoverable>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                }}
              >
                <Statistic
                  title={stat.title}
                  value={stat.value}
                  valueStyle={{ color: stat.color }}
                />
                {stat.icon}
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Card title="最近活动">
        <div
          style={{
            height: 200,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            color: '#999',
          }}
        >
          暂无最近活动
        </div>
      </Card>
    </div>
  );
};

export default DashboardPage;