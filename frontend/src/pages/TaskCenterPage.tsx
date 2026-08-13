import React, { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Tag, Badge, Button, Space, Typography, Row, Col,
  Statistic, Progress, Modal, Descriptions, Timeline, message, Select,
  Empty, Tooltip,
} from 'antd';
import {
  ExperimentOutlined, CheckCircleOutlined, CloseCircleOutlined,
  SyncOutlined, PauseCircleOutlined, ReloadOutlined, DeleteOutlined,
  EyeOutlined, PlayCircleOutlined,
} from '@ant-design/icons';
import { taskApi, projectApi } from '../api/client';
import type { TaskItem, Project } from '../types';

const { Title, Text } = Typography;

const TASK_TYPE_MAP: Record<string, { label: string; color: string }> = {
  image_gen: { label: '图像生成', color: 'purple' },
  voiceover: { label: '语音合成', color: 'blue' },
  video_compose: { label: '视频合成', color: 'green' },
  script: { label: '剧本创作', color: 'orange' },
  storyboard: { label: '分镜生成', color: 'cyan' },
  asset: { label: '资产管理', color: 'geekblue' },
};

const STATUS_MAP: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  pending: { label: '等待中', color: 'default', icon: <PauseCircleOutlined /> },
  running: { label: '运行中', color: 'processing', icon: <SyncOutlined spin /> },
  completed: { label: '已完成', color: 'success', icon: <CheckCircleOutlined /> },
  failed: { label: '失败', color: 'error', icon: <CloseCircleOutlined /> },
  cancelled: { label: '已取消', color: 'warning', icon: <CloseCircleOutlined /> },
};

const TaskCenterPage: React.FC = () => {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [detailTask, setDetailTask] = useState<TaskItem | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);

  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const res = await taskApi.list(selectedProject || undefined);
      setTasks(Array.isArray(res) ? res : []);
    } catch { /* ignore */ }
    setLoading(false);
  }, [selectedProject]);

  const loadProjects = async () => {
    try {
      const res = await projectApi.list();
      setProjects(Array.isArray(res) ? res : []);
    } catch { /* ignore */ }
  };

  useEffect(() => { loadTasks(); }, [loadTasks]);
  useEffect(() => { loadProjects(); }, []);

  const handleCancel = async (id: string) => {
    try {
      await taskApi.cancel(id);
      message.success('任务已取消');
      loadTasks();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const showDetail = (task: TaskItem) => {
    setDetailTask(task);
    setDetailVisible(true);
  };

  const stats = {
    total: tasks.length,
    running: tasks.filter(t => t.status === 'running').length,
    completed: tasks.filter(t => t.status === 'completed').length,
    failed: tasks.filter(t => t.status === 'failed').length,
  };

  const columns = [
    {
      title: '任务名称', dataIndex: 'name', key: 'name', width: 200,
      render: (v: string, r: TaskItem) => (
        <Space>
          {React.createElement(STATUS_MAP[r.status]?.icon || ExperimentOutlined)}
          <Text strong>{v}</Text>
        </Space>
      ),
    },
    {
      title: '类型', dataIndex: 'type', key: 'type', width: 100,
      render: (v: string) => {
        const info = TASK_TYPE_MAP[v] || { label: v, color: 'default' };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (v: string) => {
        const info = STATUS_MAP[v] || { label: v, color: 'default' };
        return <Badge status={info.color as any} text={info.label} />;
      },
    },
    {
      title: '进度', dataIndex: 'progress', key: 'progress', width: 180,
      render: (v: number, r: TaskItem) => (
        <Tooltip title={`${r.current_step}/${r.total_steps} 步`}>
          <Progress
            percent={v}
            size="small"
            status={r.status === 'failed' ? 'exception' : r.status === 'completed' ? 'success' : 'active'}
            style={{ margin: 0 }}
          />
        </Tooltip>
      ),
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160,
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
    },
    {
      title: '操作', key: 'action', width: 120,
      render: (_: any, r: TaskItem) => (
        <Space>
          <Tooltip title="查看详情">
            <Button size="small" icon={<EyeOutlined />} onClick={() => showDetail(r)} />
          </Tooltip>
          {r.status === 'running' && (
            <Tooltip title="取消任务">
              <Button size="small" danger icon={<CloseCircleOutlined />} onClick={() => handleCancel(r.id)} />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <ExperimentOutlined /> 任务中心
          </Title>
          <Text type="secondary">管理和监控所有后台生成任务</Text>
        </Col>
        <Col>
          <Space>
            <Select
              style={{ width: 200 }}
              placeholder="按项目筛选"
              allowClear
              value={selectedProject || undefined}
              onChange={v => setSelectedProject(v || '')}
              options={projects.map(p => ({ label: p.name, value: p.id }))}
            />
            <Button icon={<ReloadOutlined />} onClick={loadTasks}>刷新</Button>
          </Space>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small"><Statistic title="总任务" value={stats.total} prefix={<ExperimentOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card size="small"><Statistic title="运行中" value={stats.running} valueStyle={{ color: '#1890ff' }} prefix={<SyncOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card size="small"><Statistic title="已完成" value={stats.completed} valueStyle={{ color: '#52c41a' }} prefix={<CheckCircleOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card size="small"><Statistic title="失败" value={stats.failed} valueStyle={{ color: '#ff4d4f' }} prefix={<CloseCircleOutlined />} /></Card>
        </Col>
      </Row>

      <Card size="small">
        <Table
          dataSource={tasks}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 15, showSizeChanger: true }}
          locale={{ emptyText: <Empty description="暂无任务" /> }}
        />
      </Card>

      <Modal
        title="任务详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={640}
      >
        {detailTask && (
          <>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="任务名称" span={2}>{detailTask.name}</Descriptions.Item>
              <Descriptions.Item label="类型">
                <Tag color={TASK_TYPE_MAP[detailTask.type]?.color}>{TASK_TYPE_MAP[detailTask.type]?.label}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Badge status={STATUS_MAP[detailTask.status]?.color as any} text={STATUS_MAP[detailTask.status]?.label} />
              </Descriptions.Item>
              <Descriptions.Item label="进度" span={2}>
                <Progress percent={detailTask.progress} size="small" />
              </Descriptions.Item>
              <Descriptions.Item label="步骤">{detailTask.current_step}/{detailTask.total_steps}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{new Date(detailTask.created_at).toLocaleString('zh-CN')}</Descriptions.Item>
              {detailTask.completed_at && (
                <Descriptions.Item label="完成时间" span={2}>
                  {new Date(detailTask.completed_at).toLocaleString('zh-CN')}
                </Descriptions.Item>
              )}
              {detailTask.error && (
                <Descriptions.Item label="错误信息" span={2}>
                  <Text type="danger">{detailTask.error}</Text>
                </Descriptions.Item>
              )}
            </Descriptions>
            {detailTask.logs && detailTask.logs.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Text strong>执行日志</Text>
                <Timeline
                  style={{ marginTop: 8 }}
                  items={detailTask.logs.map((log: any) => ({
                    children: <Text style={{ fontSize: 13 }}>{log.message}</Text>,
                  }))}
                />
              </div>
            )}
          </>
        )}
      </Modal>
    </div>
  );
};

export default TaskCenterPage;