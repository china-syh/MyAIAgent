import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert, Button, Card, Col, Form, Input, Progress, Row, Select, Space, Steps, Tag, Typography, message, Spin, Badge, Divider, Tooltip, Empty, Statistic, Descriptions,
} from 'antd';
import {
  PlayCircleOutlined, PauseCircleOutlined, ReloadOutlined,
  NodeIndexOutlined, FileTextOutlined, PictureOutlined,
  SafetyCertificateOutlined, ThunderboltOutlined,
  CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined,
  LoadingOutlined, RightCircleOutlined, EyeOutlined,
  RocketOutlined, BookOutlined, RobotOutlined, ExperimentOutlined, SkinOutlined, CrownOutlined,
} from '@ant-design/icons';
import { productionApi, projectApi } from '../api/client';
import type { Project } from '../types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

// 阶段定义
const STAGE_CONFIG: Record<string, {
  label: string; icon: React.ReactNode; color: string; description: string;
}> = {
  planning: {
    label: '故事规划',
    icon: <BookOutlined />,
    color: '#7c3aed',
    description: '分析故事结构，规划世界观、角色和场景',
  },
  writing: {
    label: '剧本生成',
    icon: <FileTextOutlined />,
    color: '#6366f1',
    description: '创作完整的剧本内容和对话',
  },
  storyboarding: {
    label: '分镜生成',
    icon: <PictureOutlined />,
    color: '#8b5cf6',
    description: '设计每个场景的构图、角度和镜头语言',
  },
  prompting: {
    label: '提示词优化',
    icon: <ThunderboltOutlined />,
    color: '#a78bfa',
    description: '生成AI绘图提示词，优化画面描述',
  },
  quality: {
    label: '质量检查',
    icon: <SafetyCertificateOutlined />,
    color: '#10b981',
    description: '检查内容一致性和质量评分',
  },
};

const STAGE_ORDER = ['planning', 'writing', 'storyboarding', 'prompting', 'quality'];

const ProductionPage: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [run, setRun] = useState<any>(null);
  const [stages, setStages] = useState<any[]>([]);
  const [currentStage, setCurrentStage] = useState<string>('');
  const [runStatus, setRunStatus] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [streamConnected, setStreamConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const [projectStoryInput, setProjectStoryInput] = useState('');

  // 加载项目列表
  useEffect(() => {
    setLoadingProjects(true);
    projectApi.list().then((res: any) => {
      const list = Array.isArray(res) ? res : res?.data || [];
      setProjects(list);
    }).catch(() => {}).finally(() => setLoadingProjects(false));
  }, []);

  // 当项目变更时，自动填充故事输入
  const handleProjectSelect = (projectId: string) => {
    const project = projects.find(p => p.id === projectId);
    if (project) {
      form.setFieldsValue({ story_input: project.story_input || '' });
      setProjectStoryInput(project.story_input || '');
    }
  };

  // 关闭 SSE 连接
  const closeStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setStreamConnected(false);
    }
  };

  // 启动 SSE 流式监听
  const startStream = (runId: string) => {
    closeStream();
    const token = localStorage.getItem('token') || '';
    const url = `/api/v1/production/runs/${runId}/stream`;
    // 使用 fetch 手动处理 SSE（兼容性更好）
    const controller = new AbortController();
    let buffer = '';

    const fetchStream = async () => {
      try {
        const response = await fetch(url, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });
        const reader = response.body?.getReader();
        if (!reader) return;
        setStreamConnected(true);
        const decoder = new TextDecoder();
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event = JSON.parse(line.slice(6));
                handleSSEEvent(event);
              } catch { /* skip invalid JSON */ }
            }
          }
        }
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          console.error('SSE error:', err);
        }
      } finally {
        setStreamConnected(false);
      }
    };
    fetchStream();
    // 保存 abort 控制器
    (window as any).__sse_controller = controller;
  };

  // 处理 SSE 事件
  const handleSSEEvent = (event: any) => {
    switch (event.type) {
      case 'snapshot':
        setRun(event.data);
        setStages(event.data.stages || []);
        setCurrentStage(event.data.current_stage || '');
        setRunStatus(event.data.status || '');
        break;
      case 'stage_start':
        setCurrentStage(event.stage);
        setRunStatus('running');
        // 更新对应阶段的状态
        setStages(prev => prev.map(s =>
          s.name === event.stage ? { ...s, status: 'running' } : s
        ));
        break;
      case 'stage_complete':
        setStages(prev => prev.map(s =>
          s.name === event.stage ? { ...s, status: 'completed', output_data: { ...s.output_data, summary: event.summary } } : s
        ));
        break;
      case 'stage_failed':
        setStages(prev => prev.map(s =>
          s.name === event.stage ? { ...s, status: 'failed', error: event.error } : s
        ));
        setRunStatus('failed');
        break;
      case 'complete':
        setRun(event.data);
        setStages(event.data.stages || []);
        setRunStatus('completed');
        setCurrentStage('completed');
        message.success('🎉 生产线全部完成！');
        closeStream();
        break;
      case 'error':
        setRunStatus('failed');
        message.error(event.message || '生产出错');
        break;
      case 'paused':
        setRunStatus('paused');
        message.info('生产线已暂停');
        break;
      case 'resumed':
        setRunStatus('running');
        message.info('生产线继续运行');
        break;
      case 'retry':
        setRunStatus('running');
        message.info(event.message);
        break;
      case 'timeout':
        message.warning('流式连接超时，请刷新页面查看最新状态');
        closeStream();
        break;
    }
  };

  // 启动生产线
  const start = async (values: any) => {
    if (!values.project_id) {
      message.warning('请选择项目');
      return;
    }
    setLoading(true);
    try {
      const res = await productionApi.start(values.project_id, {
        story_input: values.story_input || '',
        genre: values.genre || 'fantasy',
      });
      const runData = res?.data || res;
      if (runData && runData.id) {
        setRun(runData);
        setStages(runData.stages || []);
        setRunStatus(runData.status || 'running');
        setCurrentStage(runData.current_stage || 'planning');
        message.success('生产线已启动！');
        startStream(runData.id);
      }
    } catch (err: any) {
      message.error(err.message || '启动失败');
    } finally {
      setLoading(false);
    }
  };

  // 暂停
  const handlePause = async () => {
    if (!run?.id) return;
    try {
      await productionApi.pause(run.id);
    } catch (err: any) {
      message.error(err.message);
    }
  };

  // 继续
  const handleResume = async () => {
    if (!run?.id) return;
    try {
      const res = await productionApi.resume(run.id);
      const data = res?.data || res;
      if (data) startStream(run.id);
    } catch (err: any) {
      message.error(err.message);
    }
  };

  // 重试阶段
  const handleRetry = async (stageName: string) => {
    if (!run?.id) return;
    try {
      const res = await productionApi.retryStage(run.id, stageName);
      const data = res?.data || res;
      if (data) startStream(run.id);
    } catch (err: any) {
      message.error(err.message);
    }
  };

  // 前往分镜编辑器
  const goToEditor = () => {
    if (!run?.project_id) return;
    navigate(`/editor?projectId=${run.project_id}`);
  };

  // 获取阶段状态图标
  const getStageStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircleOutlined style={{ color: '#10b981' }} />;
      case 'running': return <LoadingOutlined style={{ color: '#7c3aed' }} />;
      case 'failed': return <CloseCircleOutlined style={{ color: '#ef4444' }} />;
      case 'pending': return <ClockCircleOutlined style={{ color: '#9ca3af' }} />;
      default: return <ClockCircleOutlined style={{ color: '#9ca3af' }} />;
    }
  };

  // 计算总进度
  const calcProgress = () => {
    if (!stages.length) return 0;
    const completed = stages.filter(s => s.status === 'completed').length;
    return Math.round((completed / stages.length) * 100);
  };

  // 判断运行中
  const isRunning = runStatus === 'running' || runStatus === 'pending';

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      {/* 页面标题 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <RocketOutlined /> 项目生产线
          </Title>
          <Text type="secondary">从故事输入到生成剧本、分镜、提示词的全自动流水线</Text>
        </Col>
        {run && runStatus !== 'completed' && (
          <Col>
            <Tag icon={streamConnected ? <CheckCircleOutlined /> : <ClockCircleOutlined />}
              color={streamConnected ? 'success' : 'default'}>
              {streamConnected ? '实时连接中' : '等待连接'}
            </Tag>
          </Col>
        )}
      </Row>

      <Row gutter={24}>
        {/* 左侧：启动面板 */}
        <Col span={run ? 8 : 24} style={{ transition: 'all 0.3s' }}>
          <Card
            title={<Space><RocketOutlined style={{ color: '#7c3aed' }} />启动生产</Space>}
            style={{ marginBottom: 24 }}
          >
            <Form form={form} layout="vertical" onFinish={start} initialValues={{ genre: 'fantasy' }}>
              <Form.Item name="project_id" label="选择项目" rules={[{ required: true, message: '请选择项目' }]}>
                <Select
                  showSearch
                  placeholder="选择已有项目..."
                  loading={loadingProjects}
                  onChange={handleProjectSelect}
                  optionFilterProp="label"
                  options={projects.map(p => ({
                    label: p.name || p.id,
                    value: p.id,
                  }))}
                />
              </Form.Item>
              <Form.Item name="genre" label="故事类型">
                <Select
                  options={[
                    { value: 'fantasy', label: '🧙 奇幻' },
                    { value: 'scifi', label: '🚀 科幻' },
                    { value: 'romance', label: '💕 言情' },
                    { value: 'action', label: '⚔️ 动作' },
                    { value: 'horror', label: '👻 悬疑' },
                    { value: 'wuxia', label: '🏮 武侠' },
                  ]}
                />
              </Form.Item>
              <Form.Item name="story_input" label="故事输入">
                <TextArea
                  rows={6}
                  placeholder="请输入故事梗概，留空则使用项目中已保存的故事内容"
                />
              </Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                icon={<PlayCircleOutlined />}
                size="large"
                block
                disabled={isRunning}
                style={{ background: isRunning ? '#d1d5db' : 'linear-gradient(135deg, #7c3aed, #6366f1)', border: 'none' }}
              >
                {loading ? '启动中...' : isRunning ? '运行中...' : '🚀 启动生产线'}
              </Button>
            </Form>
          </Card>

          {/* 运行状态总览 */}
          {run && (
            <Card title="运行状态" size="small">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Statistic
                  title="进度"
                  value={calcProgress()}
                  suffix="%"
                  valueStyle={{ color: runStatus === 'failed' ? '#ef4444' : '#7c3aed' }}
                />
                <Progress
                  percent={calcProgress()}
                  status={runStatus === 'failed' ? 'exception' : undefined}
                  strokeColor={{
                    '0%': '#7c3aed',
                    '100%': '#10b981',
                  }}
                />
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="状态">
                    <Tag color={
                      runStatus === 'completed' ? 'success' :
                      runStatus === 'failed' ? 'error' :
                      runStatus === 'paused' ? 'warning' : 'processing'
                    }>
                      {runStatus === 'completed' ? '已完成' :
                       runStatus === 'failed' ? '失败' :
                       runStatus === 'paused' ? '已暂停' :
                       runStatus === 'running' ? '运行中' : '等待中'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="当前阶段">
                    {currentStage ? STAGE_CONFIG[currentStage]?.label || currentStage : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="已完成">
                    {stages.filter(s => s.status === 'completed').length} / {stages.length} 阶段
                  </Descriptions.Item>
                </Descriptions>

                {run.error && (
                  <Alert type="error" showIcon message={run.error} style={{ marginTop: 8 }} />
                )}

                <Space style={{ marginTop: 8, width: '100%' }}>
                  {runStatus === 'running' && (
                    <Button icon={<PauseCircleOutlined />} onClick={handlePause} block size="small">
                      暂停
                    </Button>
                  )}
                  {(runStatus === 'paused' || runStatus === 'failed') && (
                    <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleResume} block size="small">
                      继续运行
                    </Button>
                  )}
                  {runStatus === 'completed' && (
                    <Button type="primary" icon={<EyeOutlined />} onClick={goToEditor} block size="small">
                      查看分镜
                    </Button>
                  )}
                </Space>
              </Space>
            </Card>
          )}
        </Col>

        {/* 右侧：流水线可视化 */}
        {run && (
          <Col span={16}>
            {/* 流水线步骤 */}
            <Card
              title={
                <Space>
                  <NodeIndexOutlined style={{ color: '#7c3aed' }} />
                  <span>生产流水线</span>
                  {runStatus === 'completed' && <Tag color="success" icon={<CheckCircleOutlined />}>全部完成</Tag>}
                </Space>
              }
              style={{ marginBottom: 24 }}
            >
              {/* 水平管道图 */}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 0, marginBottom: 32 }}>
                {STAGE_ORDER.map((name, idx) => {
                  const stage = stages.find(s => s.name === name);
                  const status = stage?.status || 'pending';
                  const config = STAGE_CONFIG[name];
                  const isActive = currentStage === name;
                  const isLast = idx === STAGE_ORDER.length - 1;

                  return (
                    <React.Fragment key={name}>
                      <div style={{
                        flex: 1,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        position: 'relative',
                      }}>
                        {/* 阶段圆点 */}
                        <div style={{
                          width: 56,
                          height: 56,
                          borderRadius: '50%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: 22,
                          background: status === 'completed' ? config.color :
                            status === 'running' ? `${config.color}22` :
                            status === 'failed' ? '#fef2f2' : '#f3f4f6',
                          border: `3px solid ${
                            status === 'completed' ? config.color :
                            status === 'running' ? config.color :
                            status === 'failed' ? '#ef4444' : '#e5e7eb'
                          }`,
                          color: status === 'completed' ? '#fff' :
                            status === 'running' ? config.color :
                            status === 'failed' ? '#ef4444' : '#9ca3af',
                          transition: 'all 0.3s',
                          boxShadow: isActive ? `0 0 0 4px ${config.color}33` : 'none',
                          animation: isActive ? 'pulse 2s infinite' : 'none',
                        }}>
                          {status === 'completed' ? <CheckCircleOutlined /> :
                            status === 'running' ? <LoadingOutlined /> :
                            status === 'failed' ? <CloseCircleOutlined /> : config.icon}
                        </div>
                        {/* 阶段名称 */}
                        <Text strong style={{
                          marginTop: 8,
                          fontSize: 12,
                          color: status === 'completed' ? config.color :
                            status === 'running' ? config.color : '#9ca3af',
                          textAlign: 'center',
                        }}>
                          {config.label}
                        </Text>
                        {/* 阶段状态 */}
                        <Tag style={{
                          marginTop: 4,
                          fontSize: 10,
                          background: status === 'completed' ? `${config.color}15` :
                            status === 'running' ? `${config.color}10` : '#f3f4f6',
                          border: 'none',
                          color: status === 'completed' ? config.color :
                            status === 'running' ? config.color : '#9ca3af',
                        }}>
                          {status === 'completed' ? '已完成' :
                            status === 'running' ? '执行中' :
                            status === 'failed' ? '失败' : '等待'}
                        </Tag>
                      </div>
                      {/* 连接线 */}
                      {!isLast && (
                        <div style={{
                          flex: 0.5,
                          height: 3,
                          background: stages.find(s => s.name === STAGE_ORDER[idx])?.status === 'completed'
                            ? config.color : '#e5e7eb',
                          marginTop: 27,
                          borderRadius: 2,
                          transition: 'background 0.3s',
                        }} />
                      )}
                    </React.Fragment>
                  );
                })}
              </div>

              {/* 当前阶段详情 */}
              {currentStage && currentStage !== 'completed' && STAGE_CONFIG[currentStage] && (
                <div style={{
                  background: `${STAGE_CONFIG[currentStage].color}08`,
                  borderRadius: 12,
                  padding: '16px 20px',
                  border: `1px solid ${STAGE_CONFIG[currentStage].color}20`,
                  marginBottom: 16,
                }}>
                  <Space>
                    <Badge status="processing" color={STAGE_CONFIG[currentStage].color} />
                    <Text strong style={{ color: STAGE_CONFIG[currentStage].color }}>
                      当前：{STAGE_CONFIG[currentStage].label}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 13 }}>
                      {STAGE_CONFIG[currentStage].description}
                    </Text>
                  </Space>
                </div>
              )}
              {currentStage === 'completed' && (
                <div style={{
                  background: '#f0fdf4',
                  borderRadius: 12,
                  padding: '16px 20px',
                  border: '1px solid #bbf7d0',
                  marginBottom: 16,
                }}>
                  <Space>
                    <CheckCircleOutlined style={{ color: '#10b981', fontSize: 18 }} />
                    <Text strong style={{ color: '#16a34a', fontSize: 16 }}>
                      所有阶段已完成！
                    </Text>
                    <Button type="primary" size="small" icon={<EyeOutlined />} onClick={goToEditor}>
                      查看分镜成果
                    </Button>
                  </Space>
                </div>
              )}
            </Card>

            {/* 各阶段详细结果 */}
            <Card title="阶段详情" size="small">
              <Space direction="vertical" style={{ width: '100%' }}>
                {stages.map((stage) => {
                  const config = STAGE_CONFIG[stage.name] || { label: stage.name, icon: <RobotOutlined />, color: '#6366f1' };
                  const outputSummary = stage.output_data?.summary;
                  return (
                    <Card
                      key={stage.id || stage.name}
                      size="small"
                      title={
                        <Space>
                          {getStageStatusIcon(stage.status)}
                          <span>{config.label}</span>
                          {stage.status === 'running' && currentStage === stage.name && (
                            <Spin size="small" />
                          )}
                        </Space>
                      }
                      extra={
                        <Space>
                          <Tag color={
                            stage.status === 'completed' ? 'success' :
                            stage.status === 'running' ? 'processing' :
                            stage.status === 'failed' ? 'error' : 'default'
                          }>
                            {stage.status === 'completed' ? '已完成' :
                             stage.status === 'running' ? '执行中' :
                             stage.status === 'failed' ? '失败' : '等待'}
                          </Tag>
                          {stage.status === 'failed' && (
                            <Button
                              size="small"
                              type="primary"
                              danger
                              icon={<ReloadOutlined />}
                              onClick={() => handleRetry(stage.name)}
                            >
                              重试
                            </Button>
                          )}
                        </Space>
                      }
                      style={{ marginBottom: 8 }}
                    >
                      {/* 阶段输出摘要 */}
                      {stage.status === 'completed' && outputSummary && (
                        <div>
                          {stage.name === 'planning' && (
                            <Descriptions column={2} size="small">
                              {outputSummary.chapter_title && (
                                <Descriptions.Item label="章节标题">{outputSummary.chapter_title}</Descriptions.Item>
                              )}
                              {outputSummary.scene_count && (
                                <Descriptions.Item label="场景数量">{outputSummary.scene_count} 个</Descriptions.Item>
                              )}
                              {outputSummary.character_count && (
                                <Descriptions.Item label="角色数量">{outputSummary.character_count} 个</Descriptions.Item>
                              )}
                              {outputSummary.world_setting && (
                                <Descriptions.Item label="世界观" span={2}>
                                  {typeof outputSummary.world_setting === 'string'
                                    ? outputSummary.world_setting.slice(0, 100)
                                    : JSON.stringify(outputSummary.world_setting).slice(0, 100)}
                                </Descriptions.Item>
                              )}
                            </Descriptions>
                          )}
                          {stage.name === 'writing' && (
                            <Descriptions column={1} size="small">
                              {outputSummary.scene_count && (
                                <Descriptions.Item label="场景数量">{outputSummary.scene_count} 个</Descriptions.Item>
                              )}
                              {outputSummary.content_preview && (
                                <Descriptions.Item label="内容预览">
                                  <Text style={{ fontSize: 13 }} ellipsis={{ rows: 2 }}>
                                    {outputSummary.content_preview}
                                  </Text>
                                </Descriptions.Item>
                              )}
                            </Descriptions>
                          )}
                          {stage.name === 'storyboarding' && (
                            <Descriptions column={2} size="small">
                              {outputSummary.total_panels && (
                                <Descriptions.Item label="分镜总数">{outputSummary.total_panels} 个</Descriptions.Item>
                              )}
                              {outputSummary.scene_count && (
                                <Descriptions.Item label="场景数">{outputSummary.scene_count} 个</Descriptions.Item>
                              )}
                            </Descriptions>
                          )}
                          {stage.name === 'prompting' && (
                            <Descriptions column={1} size="small">
                              {outputSummary.total_prompts && (
                                <Descriptions.Item label="提示词总数">{outputSummary.total_prompts} 个</Descriptions.Item>
                              )}
                            </Descriptions>
                          )}
                          {stage.name === 'quality' && (
                            <Descriptions column={2} size="small">
                              {outputSummary.score !== undefined && (
                                <Descriptions.Item label="质量评分">
                                  <Text strong style={{ color: outputSummary.score >= 80 ? '#10b981' : '#f59e0b', fontSize: 18 }}>
                                    {outputSummary.score}/100
                                  </Text>
                                </Descriptions.Item>
                              )}
                              {outputSummary.passed !== undefined && (
                                <Descriptions.Item label="是否通过">
                                  <Tag color={outputSummary.passed ? 'success' : 'error'}>
                                    {outputSummary.passed ? '通过' : '未通过'}
                                  </Tag>
                                </Descriptions.Item>
                              )}
                              {outputSummary.issues && outputSummary.issues.length > 0 && (
                                <Descriptions.Item label="问题" span={2}>
                                  {outputSummary.issues.map((issue: string, i: number) => (
                                    <Tag key={i} color="warning" style={{ marginBottom: 4 }}>{issue}</Tag>
                                  ))}
                                </Descriptions.Item>
                              )}
                            </Descriptions>
                          )}
                        </div>
                      )}
                      {stage.error && (
                        <Alert type="error" message={stage.error} style={{ marginTop: 8 }} showIcon />
                      )}
                      {stage.status === 'pending' && (
                        <Text type="secondary" style={{ fontSize: 13 }}>等待执行...</Text>
                      )}
                      {stage.status === 'running' && (
                        <Space>
                          <LoadingOutlined style={{ color: '#7c3aed' }} />
                          <Text type="secondary">正在处理中...</Text>
                        </Space>
                      )}
                      {stage.status === 'completed' && !outputSummary && (
                        <Text type="secondary" style={{ fontSize: 13 }}>阶段已完成</Text>
                      )}
                    </Card>
                  );
                })}
              </Space>
            </Card>
          </Col>
        )}
      </Row>

      {/* 空状态 */}
      {!run && projects.length === 0 && (
        <Card style={{ marginTop: 24 }}>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Space direction="vertical" align="center">
                <Text type="secondary">暂无项目</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  请先在「项目列表」创建项目
                </Text>
              </Space>
            }
          >
            <Button type="primary" icon={<FileTextOutlined />} onClick={() => navigate('/projects')}>
              前往项目列表
            </Button>
          </Empty>
        </Card>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { box-shadow: 0 0 0 0 var(--pulse-color, rgba(124, 58, 237, 0.4)); }
          50% { box-shadow: 0 0 0 8px var(--pulse-color, rgba(124, 58, 237, 0)); }
        }
      `}</style>
    </div>
  );
};

export default ProductionPage;