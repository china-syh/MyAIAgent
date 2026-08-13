import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  Card, Button, Select, Modal, Form, Input, Tag, Dropdown, Tooltip,
  message, Space, Typography, Empty, Spin,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, ZoomInOutlined, ZoomOutOutlined,
  PictureOutlined, VideoCameraOutlined, AudioOutlined, FileTextOutlined,
  AppstoreOutlined, CodeOutlined, ReloadOutlined,
} from '@ant-design/icons';
import { freezoneApi, projectApi } from '../api/client';
import type { FreezoneNode, Project } from '../types';

const { Text, Title } = Typography;
const { TextArea } = Input;

// ============ 节点类型配置 ============

const NODE_TYPE_CONFIG: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  image: { color: '#7c3aed', icon: <PictureOutlined />, label: '图片' },
  video: { color: '#0891b2', icon: <VideoCameraOutlined />, label: '视频' },
  audio: { color: '#059669', icon: <AudioOutlined />, label: '音频' },
  text: { color: '#d97706', icon: <FileTextOutlined />, label: '文本' },
  storyboard: { color: '#dc2626', icon: <AppstoreOutlined />, label: '分镜' },
  script: { color: '#2563eb', icon: <CodeOutlined />, label: '脚本' },
};

const NODE_TYPES = Object.keys(NODE_TYPE_CONFIG);
const MIN_ZOOM = 0.25;
const MAX_ZOOM = 4;
const CANVAS_WIDTH = 5000;
const CANVAS_HEIGHT = 5000;

// ============ 组件 ============

const FreezonePage: React.FC = () => {
  // ---- 项目相关 ----
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | undefined>();
  const [projectsLoading, setProjectsLoading] = useState(false);

  // ---- 节点相关 ----
  const [nodes, setNodes] = useState<FreezoneNode[]>([]);
  const [nodesLoading, setNodesLoading] = useState(false);

  // ---- 画布状态 ----
  const [panX, setPanX] = useState(0);
  const [panY, setPanY] = useState(0);
  const [zoom, setZoom] = useState(1);
  const canvasRef = useRef<HTMLDivElement>(null);

  // ---- 拖拽状态 ----
  const [dragging, setDragging] = useState<{
    type: 'canvas' | 'node';
    nodeId?: string;
    startX: number;
    startY: number;
    origPanX: number;
    origPanY: number;
    origNodeX?: number;
    origNodeY?: number;
  } | null>(null);

  // ---- 编辑弹窗 ----
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingNode, setEditingNode] = useState<FreezoneNode | null>(null);
  const [editForm] = Form.useForm();
  const [saving, setSaving] = useState(false);

  // ---- 新建弹窗 ----
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createForm] = Form.useForm();
  const [creating, setCreating] = useState(false);

  // ============ 获取项目列表 ============

  const fetchProjects = useCallback(async () => {
    setProjectsLoading(true);
    try {
      const res = await projectApi.list();
      setProjects(Array.isArray(res) ? res : []);
    } catch (err: any) {
      message.error('获取项目列表失败: ' + (err?.message || '未知错误'));
    } finally {
      setProjectsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // ============ 获取节点列表 ============

  const fetchNodes = useCallback(async (projectId: string) => {
    setNodesLoading(true);
    try {
      const res = await freezoneApi.list(projectId);
      setNodes(Array.isArray(res) ? res : []);
    } catch (err: any) {
      message.error('获取节点列表失败: ' + (err?.message || '未知错误'));
      setNodes([]);
    } finally {
      setNodesLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      fetchNodes(selectedProjectId);
      setPanX(0);
      setPanY(0);
      setZoom(1);
    } else {
      setNodes([]);
    }
  }, [selectedProjectId, fetchNodes]);

  // ============ 画布交互：缩放（滚轮 + Ctrl） ============

  const handleWheel = useCallback((e: React.WheelEvent) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      setZoom((prev) => {
        const newZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, prev + delta));
        const rect = canvasRef.current?.getBoundingClientRect();
        if (rect) {
          const mouseX = e.clientX - rect.left;
          const mouseY = e.clientY - rect.top;
          setPanX((p) => mouseX - (mouseX - p) * (newZoom / prev));
          setPanY((p) => mouseY - (mouseY - p) * (newZoom / prev));
        }
        return newZoom;
      });
    }
  }, []);

  // ============ 画布交互：平移/拖拽 ============

  /** 鼠标按下：画布背景 -> 平移；节点 -> 拖拽 */
  const handleCanvasMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if ((e.target as HTMLElement).closest('.freezone-node')) return;
      if (e.button === 0) {
        setDragging({
          type: 'canvas',
          startX: e.clientX,
          startY: e.clientY,
          origPanX: panX,
          origPanY: panY,
        });
      }
    },
    [panX, panY],
  );

  const handleNodeMouseDown = useCallback(
    (e: React.MouseEvent, node: FreezoneNode) => {
      e.stopPropagation();
      if (e.button === 0) {
        setDragging({
          type: 'node',
          nodeId: node.id,
          startX: e.clientX,
          startY: e.clientY,
          origPanX: panX,
          origPanY: panY,
          origNodeX: node.position_x,
          origNodeY: node.position_y,
        });
      }
    },
    [panX, panY],
  );

  /** 全局鼠标移动/抬起（用 useEffect 绑定 window 级别事件，保证拖拽不掉） */
  useEffect(() => {
    if (!dragging) return;

    const handleMove = (e: MouseEvent) => {
      const dx = (e.clientX - dragging.startX) / zoom;
      const dy = (e.clientY - dragging.startY) / zoom;

      if (dragging.type === 'canvas') {
        setPanX(dragging.origPanX + dx);
        setPanY(dragging.origPanY + dy);
      } else if (dragging.type === 'node' && dragging.nodeId) {
        setNodes((prev) =>
          prev.map((n) =>
            n.id === dragging.nodeId
              ? {
                  ...n,
                  position_x: Math.round((dragging.origNodeX ?? 0) + dx),
                  position_y: Math.round((dragging.origNodeY ?? 0) + dy),
                }
              : n,
          ),
        );
      }
    };

    const handleUp = async () => {
      if (dragging.type === 'node' && dragging.nodeId && selectedProjectId) {
        const updatedNode = nodes.find((n) => n.id === dragging.nodeId);
        if (updatedNode) {
          try {
            await freezoneApi.update(selectedProjectId, updatedNode.id, {
              position_x: updatedNode.position_x,
              position_y: updatedNode.position_y,
            });
          } catch {
            // 拖拽位置同步失败静默处理
          }
        }
      }
      setDragging(null);
    };

    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
    };
  }, [dragging, zoom, nodes, selectedProjectId]);

  // ============ 新建节点 ============

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      setCreating(true);
      if (!selectedProjectId) {
        message.error('请先选择一个项目');
        return;
      }
      // 随机落在当前视口附近
      const viewportCenterX = (window.innerWidth / 2 - panX) / zoom - 100;
      const viewportCenterY = (window.innerHeight / 2 - panY) / zoom - 50;
      const newNode = await freezoneApi.create(selectedProjectId, {
        ...values,
        position_x: Math.round(viewportCenterX + Math.random() * 200),
        position_y: Math.round(viewportCenterY + Math.random() * 200),
        width: 220,
        height: 120,
      });
      setNodes((prev) => [...prev, newNode]);
      message.success('节点创建成功');
      setCreateModalOpen(false);
      createForm.resetFields();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error('创建节点失败: ' + (err?.message || '未知错误'));
    } finally {
      setCreating(false);
    }
  };

  // ============ 删除节点 ============

  const handleDelete = async (nodeId: string) => {
    if (!selectedProjectId) return;
    try {
      await freezoneApi.delete(selectedProjectId, nodeId);
      setNodes((prev) => prev.filter((n) => n.id !== nodeId));
      message.success('节点已删除');
    } catch (err: any) {
      message.error('删除节点失败: ' + (err?.message || '未知错误'));
    }
  };

  // ============ 编辑节点（双击） ============

  const handleDoubleClick = (node: FreezoneNode) => {
    setEditingNode(node);
    editForm.setFieldsValue({
      title: node.title,
      content:
        typeof node.content === 'object'
          ? JSON.stringify(node.content, null, 2)
          : node.content ?? '',
      tags: node.tags ?? [],
    });
    setEditModalOpen(true);
  };

  const handleSaveEdit = async () => {
    try {
      const values = await editForm.validateFields();
      setSaving(true);
      if (!selectedProjectId || !editingNode) return;

      let content: unknown = values.content;
      try {
        content = JSON.parse(values.content);
      } catch {
        // 保持字符串
      }

      const updated = await freezoneApi.update(selectedProjectId, editingNode.id, {
        title: values.title,
        content,
        tags: values.tags ?? [],
      });
      setNodes((prev) =>
        prev.map((n) => (n.id === editingNode.id ? { ...n, ...updated } : n)),
      );
      message.success('节点已更新');
      setEditModalOpen(false);
      setEditingNode(null);
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error('更新节点失败: ' + (err?.message || '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  // ============ 辅助函数 ============

  const getNodeTypeInfo = (type: string) =>
    NODE_TYPE_CONFIG[type] ?? {
      color: '#6b7280',
      icon: <FileTextOutlined />,
      label: type,
    };

  const createMenuItems = NODE_TYPES.map((type) => ({
    key: type,
    icon: <span style={{ color: NODE_TYPE_CONFIG[type].color }}>{NODE_TYPE_CONFIG[type].icon}</span>,
    label: NODE_TYPE_CONFIG[type].label,
    onClick: () => {
      createForm.setFieldsValue({ type, title: '', content: '', tags: [] });
      setCreateModalOpen(true);
    },
  }));

  // ============ 渲染 ============

  return (
    <div
      style={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: '#0f0f0f',
        color: '#e0e0e0',
      }}
    >
      {/* ---- 顶部工具栏 ---- */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '8px 16px',
          background: '#1a1a1a',
          borderBottom: '1px solid #2a2a2a',
          zIndex: 10,
          flexShrink: 0,
        }}
      >
        <Title level={5} style={{ margin: 0, color: '#e0e0e0', whiteSpace: 'nowrap' }}>
          自由画布
        </Title>

        <Select
          placeholder="选择项目"
          loading={projectsLoading}
          value={selectedProjectId}
          onChange={setSelectedProjectId}
          style={{ width: 240 }}
          allowClear
          showSearch
          optionFilterProp="label"
          options={projects.map((p) => ({ label: p.name, value: p.id }))}
        />

        <div style={{ flex: 1 }} />

        <Dropdown
          menu={{ items: createMenuItems }}
          disabled={!selectedProjectId}
          trigger={['click']}
        >
          <Button type="primary" icon={<PlusOutlined />} disabled={!selectedProjectId}>
            新建节点
          </Button>
        </Dropdown>

        <Tooltip title="缩小">
          <Button
            icon={<ZoomOutOutlined />}
            size="small"
            disabled={zoom <= MIN_ZOOM}
            onClick={() => setZoom((prev) => Math.max(MIN_ZOOM, +(prev - 0.1).toFixed(2)))}
          />
        </Tooltip>
        <Text style={{ color: '#a0a0a0', fontSize: 12, minWidth: 40, textAlign: 'center' }}>
          {Math.round(zoom * 100)}%
        </Text>
        <Tooltip title="放大">
          <Button
            icon={<ZoomInOutlined />}
            size="small"
            disabled={zoom >= MAX_ZOOM}
            onClick={() => setZoom((prev) => Math.min(MAX_ZOOM, +(prev + 0.1).toFixed(2)))}
          />
        </Tooltip>
        <Tooltip title="重置视图">
          <Button
            icon={<ReloadOutlined />}
            size="small"
            onClick={() => {
              setPanX(0);
              setPanY(0);
              setZoom(1);
            }}
          />
        </Tooltip>
      </div>

      {/* ---- 画布区域 ---- */}
      <div
        ref={canvasRef}
        style={{
          flex: 1,
          overflow: 'hidden',
          position: 'relative',
          cursor: dragging?.type === 'canvas' ? 'grabbing' : 'grab',
          background: '#0f0f0f',
          backgroundImage: 'radial-gradient(circle, #1a1a1a 1px, transparent 1px)',
          backgroundSize: '30px 30px',
        }}
        onWheel={handleWheel}
        onMouseDown={handleCanvasMouseDown}
      >
        {/* 未选择项目 */}
        {!selectedProjectId && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 5,
            }}
          >
            <Empty
              description={
                <span style={{ color: '#666' }}>请从上方选择一个项目开始创作</span>
              }
            />
          </div>
        )}

        {/* 加载中 */}
        {selectedProjectId && nodesLoading && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 5,
            }}
          >
            <Spin size="large" />
          </div>
        )}

        {/* 变换层（平移 + 缩放） */}
        <div
          style={{
            transform: `translate(${panX}px, ${panY}px) scale(${zoom})`,
            transformOrigin: '0 0',
            position: 'absolute',
            top: 0,
            left: 0,
            width: CANVAS_WIDTH,
            height: CANVAS_HEIGHT,
          }}
        >
          {/* 网格背景 */}
          <svg
            width={CANVAS_WIDTH}
            height={CANVAS_HEIGHT}
            style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
          >
            <defs>
              <pattern id="freezone-grid" width={100} height={100} patternUnits="userSpaceOnUse">
                <path
                  d="M 100 0 L 0 0 0 100"
                  fill="none"
                  stroke="#1a1a1a"
                  strokeWidth="0.5"
                />
              </pattern>
            </defs>
            <rect width={CANVAS_WIDTH} height={CANVAS_HEIGHT} fill="url(#freezone-grid)" />
          </svg>

          {/* 渲染节点 */}
          {nodes.map((node) => {
            const typeInfo = getNodeTypeInfo(node.type);
            const isDragging = dragging?.nodeId === node.id;

            return (
              <div
                key={node.id}
                className="freezone-node"
                style={{
                  position: 'absolute',
                  left: node.position_x,
                  top: node.position_y,
                  width: node.width || 220,
                  cursor: isDragging ? 'grabbing' : 'pointer',
                  zIndex: isDragging ? 100 : 1,
                  userSelect: 'none',
                }}
                onMouseDown={(e) => handleNodeMouseDown(e, node)}
                onDoubleClick={() => handleDoubleClick(node)}
              >
                <Card
                  size="small"
                  hoverable
                  style={{
                    borderLeft: `4px solid ${typeInfo.color}`,
                    background: '#1e1e1e',
                    borderColor: isDragging ? typeInfo.color : '#2a2a2a',
                    boxShadow: isDragging
                      ? `0 0 20px ${typeInfo.color}40`
                      : '0 2px 8px rgba(0,0,0,0.3)',
                    transition: 'box-shadow 0.2s, border-color 0.2s',
                  }}
                  styles={{ body: { padding: '8px 12px' } }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      marginBottom: 4,
                    }}
                  >
                    <span style={{ color: typeInfo.color, fontSize: 16 }}>
                      {typeInfo.icon}
                    </span>
                    <Text
                      style={{ color: '#e0e0e0', fontSize: 13, flex: 1 }}
                      ellipsis
                    >
                      {node.title || '未命名节点'}
                    </Text>
                    <Tooltip title="删除节点">
                      <Button
                        type="text"
                        size="small"
                        icon={<DeleteOutlined style={{ color: '#666', fontSize: 12 }} />}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(node.id);
                        }}
                      />
                    </Tooltip>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Tag
                      color={typeInfo.color}
                      style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px' }}
                    >
                      {typeInfo.label}
                    </Tag>
                    {node.tags?.slice(0, 2).map((tag) => (
                      <Tag
                        key={tag}
                        style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px' }}
                      >
                        {tag}
                      </Tag>
                    ))}
                    {(node.tags?.length ?? 0) > 2 && (
                      <Text style={{ color: '#666', fontSize: 10 }}>
                        +{(node.tags?.length ?? 0) - 2}
                      </Text>
                    )}
                  </div>
                </Card>
              </div>
            );
          })}

          {/* 空画布提示 */}
          {selectedProjectId && !nodesLoading && nodes.length === 0 && (
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                textAlign: 'center',
                color: '#666',
                pointerEvents: 'none',
              }}
            >
              <Empty
                description={
                  <span style={{ color: '#666' }}>
                    画布为空，点击「新建节点」开始创作
                  </span>
                }
              />
            </div>
          )}
        </div>

        {/* 右下角状态信息 */}
        <div
          style={{
            position: 'absolute',
            bottom: 16,
            right: 16,
            zIndex: 10,
            background: 'rgba(0,0,0,0.6)',
            borderRadius: 6,
            padding: '4px 10px',
            fontSize: 12,
            color: '#a0a0a0',
            pointerEvents: 'none',
          }}
        >
          {Math.round(zoom * 100)}% | {nodes.length} 个节点
        </div>
      </div>

      {/* ---- 新建节点弹窗 ---- */}
      <Modal
        title="新建节点"
        open={createModalOpen}
        onOk={handleCreate}
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        confirmLoading={creating}
        okText="创建"
        cancelText="取消"
        width={500}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="type"
            label="节点类型"
            rules={[{ required: true, message: '请选择节点类型' }]}
          >
            <Select
              placeholder="选择节点类型"
              options={NODE_TYPES.map((t) => ({
                label: (
                  <Space>
                    <span style={{ color: NODE_TYPE_CONFIG[t].color }}>
                      {NODE_TYPE_CONFIG[t].icon}
                    </span>
                    {NODE_TYPE_CONFIG[t].label}
                  </Space>
                ),
                value: t,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="title"
            label="节点标题"
            rules={[{ required: true, message: '请输入节点标题' }]}
          >
            <Input placeholder="节点标题" maxLength={100} />
          </Form.Item>
          <Form.Item name="content" label="内容">
            <TextArea rows={4} placeholder="输入节点内容（可选）" />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Select mode="tags" placeholder="输入标签后回车" />
          </Form.Item>
        </Form>
      </Modal>

      {/* ---- 编辑节点弹窗（双击触发） ---- */}
      <Modal
        title={editingNode ? `编辑节点 - ${editingNode.title}` : '编辑节点'}
        open={editModalOpen}
        onOk={handleSaveEdit}
        onCancel={() => {
          setEditModalOpen(false);
          setEditingNode(null);
        }}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
        width={600}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="title"
            label="节点标题"
            rules={[{ required: true, message: '请输入节点标题' }]}
          >
            <Input placeholder="节点标题" maxLength={100} />
          </Form.Item>
          <Form.Item name="content" label="内容">
            <TextArea rows={8} placeholder="节点内容（JSON 对象或纯文本）" />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Select mode="tags" placeholder="输入标签后回车" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default FreezonePage;