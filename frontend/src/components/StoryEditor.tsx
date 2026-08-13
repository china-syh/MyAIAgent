import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import {
  Card, Row, Col, Typography, Tabs, Tag, Space, Empty,
  Descriptions, Table, Badge, Alert, Modal,
  Select, Spin, Input, Button, Tooltip, Image, Progress, message,
} from 'antd';
import {
  EditOutlined, NodeIndexOutlined, ThunderboltOutlined,
  SafetyCertificateOutlined, FileTextOutlined, EyeOutlined,
  CheckCircleOutlined, CameraOutlined,
  BookOutlined, ReloadOutlined, HistoryOutlined,
  PictureOutlined, VideoCameraOutlined, LoadingOutlined,
  DeleteOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { projectApi, scriptApi, taskApi } from '../api/client';
import type { Project, Storyboard, Script, TaskItem } from '../types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

// 获取后端 API 基础地址（通过 Vite proxy 访问，避免跨域问题）
const getApiBaseUrl = () => {
  return window.location.origin;
};

const StoryEditor: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>(
    searchParams.get('projectId') || ''
  );
  const [projectName, setProjectName] = useState(
    searchParams.get('projectName') || ''
  );
  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(false);
  const [activeTab, setActiveTab] = useState('storyboards');
  const [scripts, setScripts] = useState<Script[]>([]);
  const [selectedChapter, setSelectedChapter] = useState<number>(1);
  const selectedChapterRef = useRef(selectedChapter);
  selectedChapterRef.current = selectedChapter;
  const [allStoryboards, setAllStoryboards] = useState<Storyboard[]>([]);
  const [hasData, setHasData] = useState(false);

  // 生成状态跟踪
  const [generatingPanels, setGeneratingPanels] = useState<Record<string, boolean>>({});
  const [generatingVideo, setGeneratingVideo] = useState(false);
  const [generationTasks, setGenerationTasks] = useState<Record<string, TaskItem>>({});
  const pollRefMap = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map());

  // 清理所有轮询
  useEffect(() => {
    return () => {
      pollRefMap.current.forEach((interval) => clearInterval(interval));
      pollRefMap.current.clear();
    };
  }, []);

  // 停止单个任务的轮询
  const stopPolling = useCallback((taskId: string) => {
    const interval = pollRefMap.current.get(taskId);
    if (interval) {
      clearInterval(interval);
      pollRefMap.current.delete(taskId);
    }
  }, []);

  // 启动轮询检查任务状态（支持同时轮询多个任务）
  const startPolling = useCallback((taskId: string) => {
    if (pollRefMap.current.has(taskId)) return;
    const interval = setInterval(async () => {
      try {
        const res = await taskApi.get(taskId);
        const task: TaskItem = res.data || res;
        if (task) {
          setGenerationTasks(prev => ({ ...prev, [task.id]: task }));
          if (task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') {
            stopPolling(taskId);
            // 如果完成，重新加载数据以显示图片，但保留当前章节选择
            if (task.status === 'completed') {
              const currentChapter = selectedChapterRef.current;
              await loadProjectData(selectedProject);
              // 恢复当前章节，不跳转到最后一章
              setSelectedChapter(currentChapter);
            }
            // 清理生成状态
            setGeneratingPanels(prev => {
              const next = { ...prev };
              Object.keys(next).forEach(k => { if (next[k]) delete next[k]; });
              return next;
            });
            setGeneratingVideo(false);
            if (task.status === 'failed') {
              message.error(`生成失败: ${task.error || '未知错误'}`);
            } else if (task.status === 'completed') {
              message.success('生成完成！');
            }
          }
        }
      } catch {
        stopPolling(taskId);
      }
    }, 2000);
    pollRefMap.current.set(taskId, interval);
  }, [selectedProject, stopPolling]);

  useEffect(() => {
    setLoading(true);
    projectApi.list().then(res => {
      const list = Array.isArray(res) ? res : [];
      setProjects(list);
      if (selectedProject && !projectName) {
        const p = list.find(x => x.id === selectedProject);
        if (p) setProjectName(p.name);
      }
    }).catch(() => {}).finally(() => setLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!selectedProject) return;
    loadProjectData(selectedProject, true);
  }, [selectedProject]); // eslint-disable-line react-hooks/exhaustive-deps

  const currentScript = useMemo(() => {
    return scripts.find(s => s.chapter_number === selectedChapter) || null;
  }, [scripts, selectedChapter]);

  const storyboards = useMemo(() => {
    if (!currentScript) return allStoryboards;
    return allStoryboards.filter(sb => sb.script_id === currentScript.id);
  }, [allStoryboards, currentScript]);

  const loadProjectData = async (projectId: string, initialLoad: boolean = false) => {
    setLoadingData(true);
    try {
      const result = await scriptApi.executeResult(projectId);
      // API 返回 {code: 0, message: "success", data: {scripts: [...], storyboards: [...]}}
      const data = result?.data || result;
      if (data && data.scripts && data.scripts.length > 0) {
        setScripts(data.scripts);
        setAllStoryboards(data.storyboards || []);
        // 仅在首次加载时设置最后一章，后续刷新保持当前章节不变
        if (initialLoad) {
          setSelectedChapter(data.scripts[data.scripts.length - 1].chapter_number);
        }
        setHasData(true);
      } else {
        setHasData(false);
      }
      // 加载已完成的视频合成任务
      try {
        const tasks = await taskApi.list(projectId);
        if (tasks && tasks.length > 0) {
          const completedVideoTasks = tasks.filter(
            (t: any) => t.type === 'video_compose' && t.status === 'completed'
          );
          if (completedVideoTasks.length > 0) {
            setGenerationTasks(prev => {
              const newTasks = { ...prev };
              completedVideoTasks.forEach((t: any) => { newTasks[t.id] = t; });
              return newTasks;
            });
          }
        }
      } catch (e) {
        // 静默失败，不影响主流程
      }
    } catch (err) {
      setHasData(false);
      setAllStoryboards([]);
      setScripts([]);
    } finally {
      setLoadingData(false);
    }
  };

  const handleProjectChange = (val: string) => {
    setSelectedProject(val);
    setSelectedChapter(1);
    setScripts([]);
    setAllStoryboards([]);
    setGenerationTasks({});
    const p = projects.find(x => x.id === val);
    if (p) setProjectName(p.name);
    navigate(`/editor?projectId=${val}&projectName=${encodeURIComponent(p?.name || '')}`, { replace: true });
  };

  const handleDeleteChapter = (chapterNum: number) => {
    if (!selectedProject) return;
    const script = scripts.find(s => s.chapter_number === chapterNum);
    if (!script) return;
    Modal.confirm({
      title: `确认删除第 ${chapterNum} 章？`,
      icon: <ExclamationCircleOutlined />,
      content: '删除后该章节的剧本和所有分镜图片将被永久删除，且不可恢复。',
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await scriptApi.deleteScript(selectedProject, script.id);
          message.success(`第 ${chapterNum} 章已删除`);
          // 重新加载数据
          await loadProjectData(selectedProject);
          // 如果删除的是当前章节，跳转到最后一章（如果有其他章节）
          if (selectedChapter === chapterNum && scripts.length > 1) {
            const remainingScripts = await scriptApi.list(selectedProject);
            const data = remainingScripts?.data || remainingScripts;
            if (data && data.length > 0) {
              setSelectedChapter(data[data.length - 1].chapter_number);
            }
          }
        } catch (e: any) {
          message.error(e.message || '删除失败');
        }
      },
    });
  };

  const handleChapterChange = (chapterNum: number) => {
    setSelectedChapter(chapterNum);
  };

  const handleGenerateImage = async (sb: Storyboard) => {
    if (!selectedProject || !sb.prompt) {
      message.warning('该分镜没有提示词，无法生成图片');
      return;
    }
    const key = `${sb.script_id || ''}-${sb.scene_number}-${sb.panel_number}`;
    setGeneratingPanels(prev => ({ ...prev, [key]: true }));
    try {
      const res = await taskApi.generateImage({
        project_id: selectedProject,
        storyboard_id: sb.id || '',
        prompt: sb.prompt,
      });
      const task: TaskItem = res.data || res;
      if (task && task.id) {
        setGenerationTasks(prev => ({ ...prev, [task.id]: task }));
        startPolling(task.id);
        message.loading({ content: '图像生成任务已提交，正在处理...', key: task.id });
      }
    } catch (e: any) {
      setGeneratingPanels(prev => ({ ...prev, [key]: false }));
      message.error(e.message || '提交生成任务失败');
    }
  };

  const handleComposeVideo = async () => {
    if (!selectedProject) return;
    // 确保有可用的脚本 ID
    const episodeId = currentScript?.id || (scripts.length > 0 ? scripts[0].id : '');
    if (!episodeId) {
      message.warning('请先执行 Agent 生成剧本和分镜');
      setGeneratingVideo(false);
      return;
    }
    setGeneratingVideo(true);
    try {
      const res = await taskApi.composeVideo({
        project_id: selectedProject,
        episode_id: episodeId,
      });
      const task: TaskItem = res.data || res;
      if (task && task.id) {
        setGenerationTasks(prev => ({ ...prev, [task.id]: task }));
        startPolling(task.id);
        message.loading({ content: '视频合成任务已提交，正在处理...', key: task.id });
      }
    } catch (e: any) {
      setGeneratingVideo(false);
      message.error(e.message || '提交合成任务失败');
    }
  };

  const panelColors = ['#7c3aed', '#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd'];

  const groupedByScene: Record<number, Storyboard[]> = {};
  storyboards.forEach(sb => {
    const scene = sb.scene_number || 1;
    if (!groupedByScene[scene]) groupedByScene[scene] = [];
    groupedByScene[scene].push(sb);
  });

  const storyboardContent = storyboards.length > 0 ? (
    <div>
      {Object.entries(groupedByScene).map(([sceneNum, panels]) => (
        <div key={sceneNum} style={{ marginBottom: 24 }}>
          <div style={{
            background: 'linear-gradient(135deg, #7c3aed15, #6366f115)',
            padding: '8px 16px',
            borderRadius: 8,
            marginBottom: 12,
            borderLeft: '4px solid #7c3aed',
          }}>
            <Text strong style={{ fontSize: 16 }}>
              <BookOutlined /> 第 {sceneNum} 场
            </Text>
            <Text type="secondary" style={{ marginLeft: 8 }}>
              {panels.length} 个分镜
            </Text>
          </div>
          <Row gutter={[16, 16]}>
            {panels.map((sb, idx) => {
              const colorIdx = (parseInt(sceneNum) * 10 + idx) % panelColors.length;
              const genKey = `${sb.script_id || ''}-${sb.scene_number}-${sb.panel_number}`;
              const isGenerating = generatingPanels[genKey];
              const hasImage = sb.image_url && sb.image_url.length > 0;
              const imageFullUrl = hasImage ? `${getApiBaseUrl()}${sb.image_url}` : '';
              return (
                <Col span={8} key={`${sceneNum}-${idx}`}>
                  <Card
                    className="agent-card"
                    size="small"
                    title={
                      <Space>
                        <CameraOutlined style={{ color: panelColors[colorIdx] }} />
                        <span>第 {sb.panel_number} 格</span>
                      </Space>
                    }
                    extra={<Tag color={panelColors[colorIdx]}>分镜</Tag>}
                  >
                    {/* 图片区域 */}
                    <div
                      style={{
                        height: 160,
                        borderRadius: 8,
                        marginBottom: 12,
                        overflow: 'hidden',
                        position: 'relative',
                        background: !hasImage ? `linear-gradient(135deg, ${panelColors[colorIdx]}22, ${panelColors[(colorIdx + 1) % panelColors.length]}22)` : undefined,
                        border: !hasImage ? '1px dashed #d1d5db' : undefined,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      {hasImage ? (
                        <Image
                          src={imageFullUrl}
                          alt={`分镜 ${sb.panel_number}`}
                          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                          preview={{ mask: <EyeOutlined /> }}
                          fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2YwZjBmMCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0ic2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuWbvueJh+WKoOi9veWksei0pTwvdGV4dD48L3N2Zz4="
                        />
                      ) : isGenerating ? (
                        <Space direction="vertical" align="center">
                          <LoadingOutlined style={{ fontSize: 28, color: '#7c3aed' }} />
                          <Text type="secondary" style={{ fontSize: 12 }}>生成中...</Text>
                        </Space>
                      ) : (
                        <Space direction="vertical" align="center">
                          <EyeOutlined style={{ fontSize: 24, color: '#9ca3af' }} />
                          <Text type="secondary" style={{ fontSize: 12 }}>{sb.camera_angle} · {(sb.composition || '').split('，')[0]}</Text>
                        </Space>
                      )}
                    </div>

                    <Descriptions column={1} size="small" style={{ marginBottom: 8 }}>
                      <Descriptions.Item label="构图">{sb.composition}</Descriptions.Item>
                      <Descriptions.Item label="角度">
                        <Tag>{sb.camera_angle}</Tag>
                      </Descriptions.Item>
                    </Descriptions>
                    <Paragraph type="secondary" style={{ fontSize: 13, marginBottom: 4 }} ellipsis={{ rows: 2 }}>
                      {sb.description}
                    </Paragraph>
                    {sb.dialogue && (
                      <div style={{
                        background: '#f5f3ff',
                        borderRadius: 6,
                        padding: '6px 10px',
                        marginTop: 8,
                        borderLeft: '3px solid #7c3aed',
                      }}>
                        <Text style={{ fontSize: 13, color: '#5b21b6' }}>
                          💬 {sb.dialogue}
                        </Text>
                      </div>
                    )}

                    {/* 生图按钮 */}
                    {sb.prompt && (
                      <div style={{ marginTop: 10 }}>
                        {hasImage ? (
                          <Tag icon={<CheckCircleOutlined />} color="success" style={{ fontSize: 11 }}>
                            已生成图片
                          </Tag>
                        ) : (
                          <Button
                            type="primary"
                            size="small"
                            icon={isGenerating ? <LoadingOutlined /> : <PictureOutlined />}
                            onClick={() => handleGenerateImage(sb)}
                            loading={isGenerating}
                            ghost
                            style={{ width: '100%' }}
                          >
                            {isGenerating ? '生成中...' : '生图'}
                          </Button>
                        )}
                      </div>
                    )}
                  </Card>
                </Col>
              );
            })}
          </Row>
        </div>
      ))}

      {/* 视频合成 - 检查当前章节是否已有完成视频 */}
      {(() => {
        const episodeId = currentScript?.id || '';
        const existingVideo = Object.values(generationTasks).find(
          t => t.type === 'video_compose' && t.status === 'completed' && (t.result?.episode_id === episodeId)
        );
        const hasImages = storyboards.some(sb => sb.image_url && sb.image_url.length > 0);
        if (!hasImages && !existingVideo) return null;
        return (
          <div style={{ textAlign: 'center', marginTop: 24, padding: 16, background: '#f0fdf4', borderRadius: 8, border: '1px solid #bbf7d0' }}>
            <Space direction="vertical" align="center" style={{ width: '100%' }}>
              {existingVideo ? (
                <>
                  <Text strong style={{ color: '#16a34a', fontSize: 16 }}>
                    <VideoCameraOutlined /> 视频已生成
                  </Text>
                  <Text type="secondary">该章节视频已合成完成</Text>
                  <Button
                    type="primary"
                    icon={<VideoCameraOutlined />}
                    size="large"
                    disabled
                    style={{ background: '#16a34a', borderColor: '#16a34a', opacity: 0.6 }}
                  >
                    已合成
                  </Button>
                  {/* 视频播放器 */}
                  {(() => {
                    const result = existingVideo.result || {};
                    const videoUrl = result.video_url || '';
                    const duration = result.total_duration || 0;
                    return videoUrl ? (
                      <div style={{ marginTop: 16, width: '100%', maxWidth: 720 }}>
                        <Text strong style={{ display: 'block', marginBottom: 8 }}>
                          视频已生成（{duration}秒 · {result.panel_count || 0}个分镜）
                        </Text>
                        <video
                          controls
                          style={{ width: '100%', borderRadius: 8, boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}
                          poster={result.cover_url ? `${getApiBaseUrl()}${result.cover_url}` : undefined}
                        >
                          <source src={`${getApiBaseUrl()}${videoUrl}`} type="video/mp4" />
                          您的浏览器不支持视频播放
                        </video>
                      </div>
                    ) : null;
                  })()}
                </>
              ) : (
                <>
                  <Text strong style={{ color: '#16a34a', fontSize: 16 }}>
                    <VideoCameraOutlined /> 素材就绪
                  </Text>
                  <Text type="secondary">已有分镜生成了图片，可以合成视频</Text>
                  <Button
                    type="primary"
                    icon={generatingVideo ? <LoadingOutlined /> : <VideoCameraOutlined />}
                    onClick={handleComposeVideo}
                    loading={generatingVideo}
                    size="large"
                    style={{ background: '#16a34a', borderColor: '#16a34a' }}
                  >
                    {generatingVideo ? '合成中...' : '合成视频'}
                  </Button>
                </>
              )}
            </Space>
          </div>
        );
      })()}
    </div>
  ) : (
    <Alert
      message="暂无分镜数据"
      description="请先在「Agent 监控」中执行项目，生成剧本和分镜"
      type="info"
      showIcon
      action={
        <Button size="small" onClick={() => navigate('/agent')}>
          前往执行
        </Button>
      }
    />
  );

  const promptContent = (
    <div>
      {storyboards.filter(sb => sb.prompt).length > 0 ? (
        storyboards.filter(sb => sb.prompt).map((sb, idx) => (
          <Card
            key={idx}
            className="agent-card"
            size="small"
            title={
              <Space>
                <ThunderboltOutlined style={{ color: '#f59e0b' }} />
                <span>第 {sb.scene_number} 场 · 第 {sb.panel_number} 格提示词</span>
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            <div style={{ marginBottom: 12 }}>
              <Text strong style={{ color: '#059669', display: 'block', marginBottom: 4 }}>
                <CheckCircleOutlined /> 正向提示词
              </Text>
              <TextArea
                value={sb.prompt}
                rows={2}
                readOnly
                style={{
                  background: '#f0fdf4',
                  border: '1px solid #a7f3d0',
                  color: '#065f46',
                  fontSize: 13,
                }}
              />
            </div>
            <div style={{ marginTop: 8 }}>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="场景">第 {sb.scene_number} 场</Descriptions.Item>
                <Descriptions.Item label="构图">{sb.composition}</Descriptions.Item>
              </Descriptions>
            </div>
          </Card>
        ))
      ) : (
        <Alert
          message="暂无提示词数据"
          description="分镜提示词将在 Agent 执行时自动生成"
          type="info"
          showIcon
        />
      )}
    </div>
  );

  const qualityContent = (
    <div>
      <Card
        className="agent-card"
        size="small"
        title={
          <Space>
            <SafetyCertificateOutlined style={{ color: '#10b981' }} />
            <span>质量检查报告</span>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        {currentScript ? (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="总章节数" span={2}>
              <Text strong style={{ color: '#7c3aed', fontSize: 20 }}>{scripts.length}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="当前章节">
              <Badge status="success" text={<Text strong>第 {currentScript.chapter_number} 章</Text>} />
            </Descriptions.Item>
            <Descriptions.Item label="章节状态">
              <Badge status={currentScript.status === 'completed' ? 'success' : 'processing'} text={
                <Text strong style={{ color: currentScript.status === 'completed' ? '#10b981' : '#eab308' }}>
                  {currentScript.status === 'completed' ? '已完成' : '草稿'}
                </Text>
              } />
            </Descriptions.Item>
            <Descriptions.Item label="分镜数量">
              <Text strong style={{ color: '#7c3aed', fontSize: 20 }}>{storyboards.length}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="场景数量">
              <Text strong style={{ color: '#6366f1', fontSize: 20 }}>{Object.keys(groupedByScene).length}</Text>
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Alert message="暂无质量检查数据" type="info" showIcon />
        )}
      </Card>

      {storyboards.length > 0 && (
        <Card
          className="agent-card"
          size="small"
          title="分镜概览"
          style={{ marginBottom: 16 }}
        >
          <Table
            dataSource={storyboards}
            rowKey={(_, idx) => String(idx)}
            size="small"
            pagination={{ pageSize: 5 }}
            columns={[
              { title: '场景', dataIndex: 'scene_number', width: 60, render: (v) => `第${v}场` },
              { title: '分镜', dataIndex: 'panel_number', width: 60, render: (v) => `#${v}` },
              { title: '构图', dataIndex: 'composition', ellipsis: true },
              { title: '角度', dataIndex: 'camera_angle', width: 80, render: (v) => <Tag>{v}</Tag> },
              {
                title: '对话', dataIndex: 'dialogue', ellipsis: true,
                render: (v) => v ? <Text italic>{v}</Text> : <Text type="secondary">-</Text>,
              },
              {
                title: '图片', key: 'image_url', width: 80,
                render: (_, r) => r.image_url ? <Tag color="success" icon={<CheckCircleOutlined />}>已生成</Tag> : <Tag>待生成</Tag>,
              },
            ]}
          />
        </Card>
      )}
    </div>
  );

  const tabItems = [
    {
      key: 'storyboards',
      label: <Space><NodeIndexOutlined />分镜面板 ({storyboards.length})</Space>,
      children: storyboardContent,
    },
    {
      key: 'prompts',
      label: <Space><ThunderboltOutlined />提示词 ({storyboards.filter(sb => sb.prompt).length})</Space>,
      children: promptContent,
    },
    {
      key: 'quality',
      label: <Space><SafetyCertificateOutlined />质量检查</Space>,
      children: qualityContent,
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <EditOutlined /> 分镜编辑器
          </Title>
          {projectName && (
            <Text type="secondary" style={{ marginTop: 4, display: 'block' }}>
              当前项目：{projectName}
            </Text>
          )}
        </Col>
        <Col>
          <Space>
            <Text type="secondary">选择项目：</Text>
            <Select
              style={{ width: 240 }}
              placeholder="查看项目成果"
              loading={loading}
              value={selectedProject || undefined}
              onChange={handleProjectChange}
              options={projects
                .filter(p => p.status === 'completed')
                .map(p => ({ label: p.name, value: p.id }))}
              allowClear
            />
            {hasData && scripts.length > 1 && (
              <>
                <Select
                  style={{ width: 160 }}
                  value={selectedChapter}
                  onChange={handleChapterChange}
                  options={scripts.map(s => ({
                    label: `第 ${s.chapter_number} 章`,
                    value: s.chapter_number,
                  }))}
                  prefix={<HistoryOutlined />}
                />
                <Tooltip title="删除当前章节">
                  <Button
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => handleDeleteChapter(selectedChapter)}
                  />
                </Tooltip>
              </>
            )}
            {selectedProject && (
              <Button
                icon={<ReloadOutlined />}
                onClick={() => loadProjectData(selectedProject)}
                loading={loadingData}
              >
                刷新
              </Button>
            )}
          </Space>
        </Col>
      </Row>

      {!selectedProject ? (
        <Card>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Space direction="vertical" align="center">
                <Text type="secondary">选择已完成的项目查看分镜成果</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  或者在「项目列表」创建项目 → 「Agent 监控」执行工作流
                </Text>
              </Space>
            }
          >
            <Button
              type="primary"
              icon={<FileTextOutlined />}
              onClick={() => navigate('/projects')}
            >
              前往项目列表
            </Button>
          </Empty>
        </Card>
      ) : (
        <Spin spinning={loadingData}>
          {currentScript && (
            <Card
              size="small"
              style={{ marginBottom: 16 }}
              title={
                <Space>
                  <FileTextOutlined style={{ color: '#7c3aed' }} />
                  <span>剧本：{currentScript.title || `第 ${currentScript.chapter_number} 章`}</span>
                  <Tag color="green">{currentScript.status === 'completed' ? '已完成' : '草稿'}</Tag>
                </Space>
              }
            >
              <Paragraph
                style={{ fontSize: 14, lineHeight: 1.8 }}
                ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
              >
                {currentScript.content || '暂无剧本内容'}
              </Paragraph>
              {currentScript.scenes && currentScript.scenes.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 13 }}>场景列表：</Text>
                  <Space wrap style={{ marginLeft: 8 }}>
                    {(currentScript.scenes as any[]).map((scene: any, idx: number) => (
                      <Tag key={idx} color="purple">
                        第 {scene.scene_number} 场：{scene.title || scene.description || ''}
                      </Tag>
                    ))}
                  </Space>
                </div>
              )}
            </Card>
          )}

          {!hasData && !loadingData && (
            <Alert
              type="warning"
              showIcon
              message="该项目暂无生成内容"
              description="请前往「Agent 监控」选择此项目并执行工作流以生成剧本和分镜"
              action={
                <Button size="small" onClick={() => navigate('/agent')}>
                  前往执行
                </Button>
              }
              style={{ marginBottom: 16 }}
            />
          )}

          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabItems}
            size="large"
          />
        </Spin>
      )}
    </div>
  );
};

export default StoryEditor;