import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  Card, Button, Select, Typography, Steps, Tag, Space, Alert,
  Spin, Descriptions, Divider, Badge, Input, Row, Col, message,
  Statistic, Empty, Timeline, Result, Modal,
} from 'antd';
import {
  RobotOutlined, PlayCircleOutlined, StopOutlined,
  ReloadOutlined, CheckCircleOutlined, CloseCircleOutlined,
  LoadingOutlined, RightCircleOutlined, NodeIndexOutlined,
  FileTextOutlined, ThunderboltOutlined, ExperimentOutlined,
  SketchOutlined, SafetyCertificateOutlined, ArrowRightOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { projectApi, scriptApi } from '../api/client';
import type { Project, AgentEvent, Storyboard } from '../types';

const { Title, Text } = Typography;
const { TextArea } = Input;

const AGENT_STEPS = [
  { title: '策划', description: '世界观与角色', icon: <ExperimentOutlined /> },
  { title: '编剧', description: '故事剧本创作', icon: <FileTextOutlined /> },
  { title: '分镜', description: '镜头画面设计', icon: <NodeIndexOutlined /> },
  { title: '提示词', description: 'AI 绘图指令', icon: <ThunderboltOutlined /> },
  { title: '质检', description: '质量检查审核', icon: <SafetyCertificateOutlined /> },
];

const AgentMonitor: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>(
    searchParams.get('projectId') || ''
  );
  const [projectName, setProjectName] = useState(
    searchParams.get('projectName') || ''
  );
  const [storyInput, setStoryInput] = useState('');
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [currentStep, setCurrentStep] = useState(-1);
  const [abortRef, setAbortRef] = useState<AbortController | null>(null);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [resultData, setResultData] = useState<any>(null);
  const [showResultModal, setShowResultModal] = useState(false);
  const [resultStoryboards, setResultStoryboards] = useState<Storyboard[]>([]);

  const eventsEndRef = useRef<HTMLDivElement>(null);

  // 加载项目列表
  useEffect(() => {
    if (projects.length === 0) {
      setLoadingProjects(true);
      projectApi.list().then(res => {
        setProjects(Array.isArray(res) ? res : []);
      }).catch(() => {}).finally(() => setLoadingProjects(false));
    }
  }, [projects.length]);

  // 自动滚动到最新事件
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  // 更新项目名
  useEffect(() => {
    if (selectedProject && projects.length > 0) {
      const p = projects.find(x => x.id === selectedProject);
      if (p) setProjectName(p.name);
    }
  }, [selectedProject, projects]);

  const startAgent = useCallback(async () => {
    if (!selectedProject) {
      message.warning('请先选择项目');
      return;
    }

    setStatus('running');
    setEvents([]);
    setCurrentStep(-1);
    setResultData(null);
    setResultStoryboards([]);

    const abort = new AbortController();
    setAbortRef(abort);

    try {
      const response = await fetch('/api/v1/agents/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: selectedProject,
          story_input: storyInput,
        }),
        signal: abort.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: AgentEvent = JSON.parse(line.slice(6));
              setEvents(prev => {
                const updated = [...prev, event];

                // 更新当前步骤
                if (event.type === 'AGENT_START' && event.data?.node) {
                  const nodeMap: Record<string, number> = {
                    planner: 0, writer: 1, storyboarder: 2, prompter: 3, quality_checker: 4,
                  };
                  const step = nodeMap[event.data.node as string];
                  if (step !== undefined) {
                    setCurrentStep(step);
                  }
                }
                if (event.type === 'AGENT_FINISH' && event.data?.node) {
                  const nodeMap: Record<string, number> = {
                    planner: 0, writer: 1, storyboarder: 2, prompter: 3, quality_checker: 4,
                  };
                  const step = nodeMap[event.data.node as string];
                  if (step !== undefined) {
                    setCurrentStep(step + 1);
                  }
                }

                // COMPLETE 事件携带数据
                if (event.type === 'COMPLETE' && event.data) {
                  setResultData(event.data);
                  if (event.data.storyboards) {
                    setResultStoryboards(event.data.storyboards as Storyboard[]);
                  }
                }

                return updated;
              });
            } catch {
              // 忽略解析错误
            }
          }
        }
      }
      setStatus('done');
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setStatus('error');
        setEvents(prev => [...prev, {
          type: 'ERROR',
          message: '执行出错: ' + (err?.message || '未知错误'),
        }]);
      }
    } finally {
      setAbortRef(null);
    }
  }, [selectedProject, storyInput]);

  const stopAgent = () => {
    abortRef?.abort();
    setStatus('idle');
    setAbortRef(null);
  };

  const resetAgent = () => {
    setStatus('idle');
    setEvents([]);
    setCurrentStep(-1);
    setResultData(null);
    setResultStoryboards([]);
  };

  const viewResult = () => {
    if (selectedProject) {
      setShowResultModal(true);
    }
  };

  const goToEditor = () => {
    if (selectedProject) {
      navigate(`/editor?projectId=${selectedProject}&projectName=${encodeURIComponent(projectName)}`);
    }
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'AGENT_START': return <RobotOutlined style={{ color: '#7c3aed' }} />;
      case 'AGENT_FINISH': return <CheckCircleOutlined style={{ color: '#10b981' }} />;
      case 'ERROR': return <CloseCircleOutlined style={{ color: '#ef4444' }} />;
      default: return <RightCircleOutlined style={{ color: '#6366f1' }} />;
    }
  };

  const getEventColor = (type: string) => {
    switch (type) {
      case 'AGENT_START': return '#7c3aed';
      case 'AGENT_FINISH': return '#10b981';
      case 'ERROR': return '#ef4444';
      default: return '#6366f1';
    }
  };

  const panelColors = ['#7c3aed', '#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd'];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <RobotOutlined /> Agent 监控
          </Title>
        </Col>
        <Col>
          <Space>
            {status === 'running' && (
              <Button danger icon={<StopOutlined />} onClick={stopAgent}>
                停止
              </Button>
            )}
            {(status === 'done' || status === 'error') && (
              <Button icon={<ReloadOutlined />} onClick={resetAgent}>
                重置
              </Button>
            )}
            {status === 'done' && resultData && (
              <Button
                type="primary"
                icon={<EyeOutlined />}
                onClick={goToEditor}
              >
                查看内容
              </Button>
            )}
            <Button
              type="primary"
              icon={status === 'running' ? <LoadingOutlined /> : <PlayCircleOutlined />}
              onClick={startAgent}
              disabled={status === 'running' || !selectedProject}
              loading={status === 'running'}
            >
              {status === 'running' ? '执行中...' : '开始执行'}
            </Button>
          </Space>
        </Col>
      </Row>

      <Row gutter={16}>
        {/* 左侧：配置区 */}
        <Col span={8}>
          <Card title="项目配置" size="small" style={{ marginBottom: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>选择项目</Text>
                <Select
                  style={{ width: '100%' }}
                  placeholder="选择要执行的项目"
                  loading={loadingProjects}
                  value={selectedProject || undefined}
                  onChange={(val) => { setSelectedProject(val); resetAgent(); }}
                  options={projects.map(p => ({
                    label: `${p.name} (${p.genre || '未分类'})`,
                    value: p.id,
                  }))}
                  disabled={status === 'running'}
                />
              </div>
              <div>
                <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>故事输入（可选）</Text>
                <TextArea
                  rows={4}
                  placeholder="输入补充故事设定，留空则使用项目中的故事梗概"
                  value={storyInput}
                  onChange={e => setStoryInput(e.target.value)}
                  disabled={status === 'running'}
                />
              </div>
            </Space>
          </Card>

          {/* 执行状态 */}
          <Card title="执行状态" size="small">
            {status === 'idle' && (
              <Empty description="选择项目并点击「开始执行」" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
            {status === 'running' && (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Alert
                  type="info"
                  showIcon
                  icon={<LoadingOutlined />}
                  message="Agent 工作流执行中..."
                  description="正在生成漫画内容，请稍候..."
                />
                <div style={{ textAlign: 'center', marginTop: 8 }}>
                  <Statistic
                    title="已接收事件"
                    value={events.length}
                    prefix={<RobotOutlined />}
                    valueStyle={{ color: '#7c3aed' }}
                  />
                </div>
              </Space>
            )}
            {status === 'done' && (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Alert
                  type="success"
                  showIcon
                  icon={<CheckCircleOutlined />}
                  message="执行完成"
                  description="Agent 工作流已成功执行完毕"
                />
                {resultData && (
                  <div style={{ textAlign: 'center', marginTop: 8 }}>
                    <Button
                      type="primary"
                      icon={<EyeOutlined />}
                      onClick={goToEditor}
                      block
                    >
                      查看生成内容（剧本 + {resultData.storyboards?.length || 0} 个分镜）
                    </Button>
                  </div>
                )}
              </Space>
            )}
            {status === 'error' && (
              <Alert
                type="error"
                showIcon
                icon={<CloseCircleOutlined />}
                message="执行出错"
                description={events.find(e => e.type === 'ERROR')?.message || '发生未知错误'}
              />
            )}
          </Card>
        </Col>

        {/* 中间：Agent 步骤 + 结果预览 */}
        <Col span={8}>
          <Card title="Agent 工作流" size="small" style={{ marginBottom: 16 }}>
            <Steps
              direction="vertical"
              size="small"
              current={currentStep - 1}
              status={status === 'error' ? 'error' : 'process'}
              items={AGENT_STEPS.map((step, idx) => ({
                title: (
                  <span style={{
                    color: idx < currentStep ? '#10b981' : idx === currentStep ? '#7c3aed' : undefined,
                    fontWeight: idx === currentStep ? 600 : undefined,
                  }}>
                    {step.title}
                  </span>
                ),
                description: step.description,
                icon: idx < currentStep
                  ? <CheckCircleOutlined style={{ color: '#10b981' }} />
                  : idx === currentStep
                    ? <LoadingOutlined style={{ color: '#7c3aed' }} />
                    : step.icon,
                status: idx < currentStep ? 'finish'
                  : idx === currentStep ? 'process'
                    : 'wait',
              } as any))}
            />
          </Card>

          {/* 结果预览 */}
          {status === 'done' && resultData?.script && (
            <Card
              title={<Space><FileTextOutlined />剧本摘要</Space>}
              size="small"
            >
              <Descriptions column={1} size="small">
                <Descriptions.Item label="标题">{resultData.script.title}</Descriptions.Item>
                <Descriptions.Item label="章节">第 {resultData.script.chapter_number} 章</Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color="green">{resultData.script.status}</Tag>
                </Descriptions.Item>
              </Descriptions>
              <Divider style={{ margin: '8px 0' }} />
              <Text type="secondary" style={{ fontSize: 13 }}>
                {resultData.script.content?.substring(0, 120)}...
              </Text>
            </Card>
          )}

          {/* 统计信息 */}
          {events.length > 0 && (
            <Card title="事件统计" size="small" style={{ marginTop: 16 }}>
              <Row gutter={[8, 8]}>
                <Col span={12}>
                  <Statistic
                    title="启动事件"
                    value={events.filter(e => e.type === 'AGENT_START').length}
                    valueStyle={{ fontSize: 20, color: '#7c3aed' }}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="完成事件"
                    value={events.filter(e => e.type === 'AGENT_FINISH').length}
                    valueStyle={{ fontSize: 20, color: '#10b981' }}
                  />
                </Col>
              </Row>
            </Card>
          )}
        </Col>

        {/* 右侧：事件流 */}
        <Col span={8}>
          <Card
            title={
              <Space>
                <span>事件流</span>
                {status === 'running' && <Badge status="processing" text="实时" />}
                {events.length > 0 && <Tag>{events.length} 条</Tag>}
              </Space>
            }
            size="small"
            styles={{ body: { maxHeight: 520, overflow: 'auto', padding: 12 } }}
          >
            {events.length === 0 ? (
              <Empty description="暂无事件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <Timeline
                items={events.map((event, idx) => ({
                  color: getEventColor(event.type),
                  dot: getEventIcon(event.type),
                  children: (
                    <div className="event-slide-in" key={idx}>
                      <Space style={{ marginBottom: 2 }}>
                        <Tag color={getEventColor(event.type)} style={{ fontSize: 11 }}>
                          {event.type}
                        </Tag>
                        {event.data?.node && (
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {event.data.node as string}
                          </Text>
                        )}
                      </Space>
                      <div style={{ fontSize: 13, marginTop: 2 }}>
                        {event.message || JSON.stringify(event.data || {})}
                      </div>
                    </div>
                  ),
                }))}
              />
            )}
            <div ref={eventsEndRef} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AgentMonitor;