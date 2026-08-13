import React, { useEffect, useState, useCallback } from 'react';
import {
  Table, Button, Modal, Form, Input, Select, Tag, Space, Popconfirm,
  message, Empty, Card, Typography, Row, Col, Statistic, Badge, Tooltip,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, PlayCircleOutlined,
  ProjectOutlined, RobotOutlined, FileTextOutlined,
  ReloadOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { projectApi } from '../api/client';
import type { Project } from '../types';

const { Title, Text } = Typography;
const { TextArea } = Input;

const statusConfig: Record<string, { color: string; text: string }> = {
  draft: { color: 'default', text: '草稿' },
  generating: { color: 'processing', text: '生成中' },
  completed: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
};

const ProjectList: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const res = await projectApi.list();
      setProjects(Array.isArray(res) ? res : []);
    } catch (err: any) {
      message.error('获取项目列表失败: ' + (err?.message || '未知错误'));
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setCreating(true);
      await projectApi.create(values);
      message.success('项目创建成功');
      setModalOpen(false);
      form.resetFields();
      fetchProjects();
    } catch (err: any) {
      if (err?.errorFields) return; // 表单验证错误
      message.error('创建失败: ' + (err?.message || '未知错误'));
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await projectApi.delete(id);
      message.success('项目已删除');
      fetchProjects();
    } catch (err: any) {
      message.error('删除失败: ' + (err?.message || '未知错误'));
    }
  };

  const handleExecute = (project: Project) => {
    navigate(`/agent?projectId=${project.id}&projectName=${encodeURIComponent(project.name)}`);
  };

  const columns = [
    {
      title: '项目名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Project) => (
        <Space>
          <ProjectOutlined style={{ color: '#7c3aed' }} />
          <Text strong>{name}</Text>
          <Badge
            status={statusConfig[record.status]?.color as any}
            text={statusConfig[record.status]?.text || record.status}
          />
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'genre',
      key: 'genre',
      width: 120,
      render: (genre: string) => genre ? <Tag>{genre}</Tag> : '-',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc: string) => desc || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: any, record: Project) => (
        <Space>
          <Tooltip title="执行 Agent 工作流">
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleExecute(record)}
              disabled={record.status === 'generating'}
            >
              执行
            </Button>
          </Tooltip>
          <Popconfirm
            title="确认删除"
            description="删除后无法恢复，确定要删除该项目吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button danger size="small" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <ProjectOutlined /> 项目列表
          </Title>
        </Col>
        <Col>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchProjects} loading={loading}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
              新建项目
            </Button>
          </Space>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="全部项目"
              value={projects.length}
              prefix={<ProjectOutlined />}
              valueStyle={{ color: '#7c3aed' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="已完成"
              value={projects.filter(p => p.status === 'completed').length}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#10b981' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="生成中"
              value={projects.filter(p => p.status === 'generating').length}
              prefix={<RobotOutlined />}
              valueStyle={{ color: '#7c3aed' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="失败"
              value={projects.filter(p => p.status === 'failed').length}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#ef4444' }}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Table
          dataSource={projects}
          columns={columns}
          rowKey="id"
          loading={loading}
          locale={{
            emptyText: (
              <Empty description="还没有项目，点击「新建项目」开始创作">
                <Button type="primary" onClick={() => setModalOpen(true)}>
                  新建项目
                </Button>
              </Empty>
            ),
          }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个项目`,
          }}
        />
      </Card>

      <Modal
        title="新建项目"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => { setModalOpen(false); form.resetFields(); }}
        confirmLoading={creating}
        okText="创建"
        cancelText="取消"
        width={600}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="项目名称"
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input placeholder="例如：我的第一部AI漫画" maxLength={100} />
          </Form.Item>
          <Form.Item name="genre" label="漫画类型">
            <Select
              placeholder="选择类型"
              allowClear
              options={[
                { label: '热血', value: '热血' },
                { label: '恋爱', value: '恋爱' },
                { label: '奇幻', value: '奇幻' },
                { label: '科幻', value: '科幻' },
                { label: '悬疑', value: '悬疑' },
                { label: '搞笑', value: '搞笑' },
                { label: '日常', value: '日常' },
                { label: '古风', value: '古风' },
              ]}
            />
          </Form.Item>
          <Form.Item name="description" label="项目描述">
            <TextArea rows={2} placeholder="简单描述一下你的项目..." maxLength={500} />
          </Form.Item>
          <Form.Item name="story_input" label="故事梗概">
            <TextArea
              rows={4}
              placeholder="输入故事的核心创意、世界观设定、主要角色简介等..."
              maxLength={2000}
              showCount
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ProjectList;