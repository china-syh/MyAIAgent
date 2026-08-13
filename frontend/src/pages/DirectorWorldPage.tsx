import React, { useEffect, useState } from 'react';
import {
  Card, Row, Col, Button, Select, Modal, Form, Input,
  InputNumber, Tag, Descriptions, Empty, Space, Typography,
  message, Popconfirm, Tooltip, Divider, Badge, Spin,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, ReloadOutlined,
  EnvironmentOutlined, CameraOutlined, TeamOutlined,
  BranchesOutlined, EyeOutlined, SettingOutlined,
} from '@ant-design/icons';
import { directorWorldApi, projectApi } from '../api/client';
import type { DirectorWorld, Project } from '../types';

const { Title, Text } = Typography;
const { TextArea } = Input;

// ============ 俯视图 SVG 组件 ============

interface TopDownViewProps {
  cameraPosition: Record<string, unknown>;
  characterBlocking: Array<Record<string, unknown>>;
  size?: number;
}

const TopDownView: React.FC<TopDownViewProps> = ({
  cameraPosition,
  characterBlocking,
  size = 180,
}) => {
  const cx = size / 2;
  const cy = size / 2;
  const gridSize = size / 10;

  // 解析相机位置
  const camX = (cameraPosition?.x as number) ?? 0;
  const camY = (cameraPosition?.y as number) ?? 0;
  const camZ = (cameraPosition?.z as number) ?? 0;
  const camAngle = (cameraPosition?.angle as number) ?? 0;
  const camFov = (cameraPosition?.fov as number) ?? 60;

  // 归一化到网格
  const normX = (camX / 10) * size / 2 + cx;
  const normY = (camY / 10) * size / 2 + cy;

  // 相机视野三角形
  const fovRad = (camFov * Math.PI) / 180;
  const angleRad = (camAngle * Math.PI) / 180;
  const fovLen = Math.min(size * 0.35, 60);
  const fovLeft = {
    x: normX + fovLen * Math.cos(angleRad - fovRad / 2),
    y: normY + fovLen * Math.sin(angleRad - fovRad / 2),
  };
  const fovRight = {
    x: normX + fovLen * Math.cos(angleRad + fovRad / 2),
    y: normY + fovLen * Math.sin(angleRad + fovRad / 2),
  };

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* 背景网格 */}
      <defs>
        <pattern id="grid" width={gridSize} height={gridSize} patternUnits="userSpaceOnUse">
          <path d={`M ${gridSize} 0 L 0 0 0 ${gridSize}`} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={0.5} />
        </pattern>
        <radialGradient id="camGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#7c3aed" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#7c3aed" stopOpacity="0" />
        </radialGradient>
        <filter id="shadow">
          <feDropShadow dx="0" dy="1" stdDeviation="2" floodOpacity="0.3" />
        </filter>
      </defs>
      <rect width={size} height={size} fill="#1a1a2e" rx={8} />
      <rect width={size} height={size} fill="url(#grid)" rx={8} />

      {/* 安全框 */}
      <rect
        x={size * 0.15} y={size * 0.15}
        width={size * 0.7} height={size * 0.7}
        fill="none" stroke="rgba(255,255,255,0.08)"
        strokeWidth={1} strokeDasharray="4 2"
        rx={4}
      />

      {/* 角色阻挡 */}
      {characterBlocking.map((cb, idx) => {
        const bx = ((cb?.x as number) ?? 0) / 10 * size / 2 + cx;
        const by = ((cb?.y as number) ?? 0) / 10 * size / 2 + cy;
        const charName = (cb?.character_name as string) ?? (cb?.character as string) ?? `角色${idx + 1}`;
        const color = (cb?.color as string) ?? '#4f46e5';
        return (
          <g key={idx} filter="url(#shadow)">
            <circle cx={bx} cy={by} r={8} fill={color} opacity={0.9} />
            <circle cx={bx} cy={by} r={12} fill="none" stroke={color} strokeWidth={1} opacity={0.4} />
            <text
              x={bx} y={by + 4}
              textAnchor="middle" fill="#fff"
              fontSize={7} fontWeight="bold"
            >
              {idx + 1}
            </text>
            <text
              x={bx} y={by + 20}
              textAnchor="middle" fill="rgba(255,255,255,0.5)"
              fontSize={6}
            >
              {charName.length > 6 ? charName.slice(0, 6) + '..' : charName}
            </text>
          </g>
        );
      })}

      {/* 相机视野渐变 */}
      <polygon
        points={`${normX},${normY} ${fovLeft.x},${fovLeft.y} ${fovRight.x},${fovRight.y}`}
        fill="url(#camGlow)"
      />

      {/* 相机视野线 */}
      <line x1={normX} y1={normY} x2={fovLeft.x} y2={fovLeft.y} stroke="#7c3aed" strokeWidth={1} opacity={0.5} />
      <line x1={normX} y1={normY} x2={fovRight.x} y2={fovRight.y} stroke="#7c3aed" strokeWidth={1} opacity={0.5} />

      {/* 相机图标 */}
      <g filter="url(#shadow)">
        <circle cx={normX} cy={normY} r={6} fill="#7c3aed" />
        <circle cx={normX} cy={normY} r={10} fill="none" stroke="#7c3aed" strokeWidth={1.5} opacity={0.6} />
        <text
          x={normX} y={normY + 4}
          textAnchor="middle" fill="#fff"
          fontSize={7} fontWeight="bold"
        >
          C
        </text>
      </g>

      {/* 右下角图例 */}
      <g transform={`translate(${size - 45}, ${size - 18})`} opacity={0.5}>
        <rect x={0} y={0} width={10} height={10} rx={2} fill="#7c3aed" />
        <text x={14} y={9} fill="rgba(255,255,255,0.6)" fontSize={7}>CAM</text>
        <rect x={0} y={14} width={10} height={10} rx={2} fill="#4f46e5" />
        <text x={14} y={23} fill="rgba(255,255,255,0.6)" fontSize={7}>CHAR</text>
      </g>
    </svg>
  );
};

// ============ 格式化工具 ============

const formatCameraPos = (pos: Record<string, unknown>): string => {
  const x = (pos?.x as number) ?? 0;
  const y = (pos?.y as number) ?? 0;
  const z = (pos?.z as number) ?? 0;
  return `(${x.toFixed(1)}, ${y.toFixed(1)}, ${z.toFixed(1)})`;
};

// ============ 主页面 ============

const DirectorWorldPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [worlds, setWorlds] = useState<DirectorWorld[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  // 加载项目列表
  useEffect(() => {
    projectApi.list()
      .then(res => setProjects(Array.isArray(res) ? res : []))
      .catch(() => {});
  }, []);

  // 加载世界列表
  useEffect(() => {
    if (!selectedProject) {
      setWorlds([]);
      return;
    }
    loadWorlds();
  }, [selectedProject]);

  const loadWorlds = async () => {
    setLoading(true);
    try {
      const res = await directorWorldApi.list(selectedProject);
      setWorlds(Array.isArray(res) ? res : []);
    } catch {
      message.error('加载导演世界失败');
    }
    setLoading(false);
  };

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();

      // 构建 camera_position
      const cameraPosition: Record<string, unknown> = {
        x: values.camera_x ?? 0,
        y: values.camera_y ?? 0,
        z: values.camera_z ?? 5,
        angle: values.camera_angle ?? 0,
        fov: values.camera_fov ?? 60,
      };

      // 构建 character_blocking
      const characterBlocking: Array<Record<string, unknown>> = [];
      if (values.characters) {
        values.characters.forEach((ch: any, idx: number) => {
          if (ch.name) {
            characterBlocking.push({
              character_name: ch.name,
              x: ch.x ?? 0,
              y: ch.y ?? 0,
              color: ch.color ?? '#4f46e5',
            });
          }
        });
      }

      await directorWorldApi.create(selectedProject, {
        name: values.name,
        description: values.description,
        scene_id: values.scene_id || null,
        camera_position: cameraPosition,
        character_blocking: characterBlocking,
      });

      message.success('导演世界创建成功');
      setModalVisible(false);
      form.resetFields();
      loadWorlds();
    } catch (e: any) {
      if (e.message) message.error(e.message);
    }
  };

  const handleDelete = async (worldId: string) => {
    try {
      await directorWorldApi.delete(selectedProject, worldId);
      message.success('导演世界已删除');
      loadWorlds();
    } catch (e: any) {
      if (e.message) message.error(e.message);
    }
  };

  const projectSelector = (
    <Space>
      <Text type="secondary" style={{ fontSize: 13 }}>选择项目：</Text>
      <Select
        style={{ width: 240 }}
        placeholder="选择项目查看导演世界"
        value={selectedProject || undefined}
        onChange={v => setSelectedProject(v)}
        options={projects.map(p => ({ label: p.name, value: p.id }))}
        allowClear
      />
      <Tooltip title="刷新">
        <Button icon={<ReloadOutlined />} onClick={loadWorlds} loading={loading} />
      </Tooltip>
    </Space>
  );

  // 渲染一个世界卡片
  const renderWorldCard = (world: DirectorWorld) => {
    const cameraPos = (world.camera_position ?? {}) as Record<string, unknown>;
    const charBlocking = (world.character_blocking ?? []) as Array<Record<string, unknown>>;
    const variants = (world.variants ?? []) as Array<Record<string, unknown>>;
    const variantCount = variants.length;

    return (
      <Col xs={24} sm={12} lg={8} xl={6} key={world.id}>
        <Card
          className="director-world-card"
          style={{
            borderRadius: 12,
            overflow: 'hidden',
            border: '1px solid rgba(124, 58, 237, 0.15)',
            background: 'linear-gradient(135deg, rgba(30, 27, 75, 0.95) 0%, rgba(15, 15, 35, 0.95) 100%)',
            height: '100%',
          }}
          bodyStyle={{ padding: 0 }}
        >
          {/* 俯视图区域 */}
          <div style={{ position: 'relative' }}>
            {cameraPos && Object.keys(cameraPos).length > 0 ? (
              <TopDownView
                cameraPosition={cameraPos}
                characterBlocking={charBlocking}
                size={200}
              />
            ) : (
              <div
                style={{
                  height: 200,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#1a1a2e',
                  borderRadius: '12px 12px 0 0',
                  flexDirection: 'column',
                  gap: 8,
                }}
              >
                <CameraOutlined style={{ fontSize: 28, color: 'rgba(255,255,255,0.2)' }} />
                <Text style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>未设置相机位置</Text>
              </div>
            )}

            {/* 状态标签 */}
            <div style={{ position: 'absolute', top: 8, left: 8 }}>
              <Badge
                status={world.status === 'active' ? 'success' : 'default'}
                text={world.status === 'active' ? '已启用' : '未启用'}
                style={{ color: 'rgba(255,255,255,0.7)' }}
              />
            </div>

            {/* 变体数量标签 */}
            <div style={{ position: 'absolute', top: 8, right: 8 }}>
              <Tag
                icon={<BranchesOutlined />}
                color="purple"
                style={{ borderRadius: 8, border: 'none' }}
              >
                {variantCount} 变体
              </Tag>
            </div>
          </div>

          {/* 信息区域 */}
          <div style={{ padding: '12px 16px 16px' }}>
            {/* 标题 */}
            <div style={{ marginBottom: 8 }}>
              <Text strong style={{ color: '#fff', fontSize: 15, display: 'block' }}>
                {world.name || '未命名场景'}
              </Text>
              {world.description && (
                <Text style={{ color: 'rgba(255,255,255,0.5)', fontSize: 12, display: 'block', marginTop: 2 }}>
                  {world.description.length > 50
                    ? world.description.slice(0, 50) + '...'
                    : world.description}
                </Text>
              )}
            </div>

            <Divider style={{ margin: '8px 0', borderColor: 'rgba(124,58,237,0.1)' }} />

            {/* 详细信息 */}
            <Descriptions column={1} size="small" colon={false}>
              <Descriptions.Item
                label={
                  <Space size={4}>
                    <CameraOutlined style={{ color: '#7c3aed', fontSize: 12 }} />
                    <Text style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>相机</Text>
                  </Space>
                }
              >
                <Text style={{ color: 'rgba(255,255,255,0.7)', fontSize: 12, fontFamily: 'monospace' }}>
                  {cameraPos && Object.keys(cameraPos).length > 0
                    ? formatCameraPos(cameraPos)
                    : '--'}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item
                label={
                  <Space size={4}>
                    <TeamOutlined style={{ color: '#4f46e5', fontSize: 12 }} />
                    <Text style={{ color: 'rgba(255,255,255,0.45)', fontSize: 12 }}>角色</Text>
                  </Space>
                }
              >
                <Text style={{ color: 'rgba(255,255,255,0.7)', fontSize: 12 }}>
                  {charBlocking.length > 0
                    ? `${charBlocking.length} 个角色`
                    : '未设置'}
                </Text>
              </Descriptions.Item>
            </Descriptions>

            {/* 角色标签 */}
            {charBlocking.length > 0 && (
              <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {charBlocking.map((cb, idx) => {
                  const name = (cb?.character_name as string) ?? (cb?.character as string) ?? `角色${idx + 1}`;
                  const color = (cb?.color as string) ?? '#4f46e5';
                  return (
                    <Tag
                      key={idx}
                      color={color}
                      style={{ borderRadius: 4, border: 'none', fontSize: 11 }}
                    >
                      {name}
                    </Tag>
                  );
                })}
              </div>
            )}

            {/* 底部操作栏 */}
            <Divider style={{ margin: '10px 0 0', borderColor: 'rgba(124,58,237,0.1)' }} />
            <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: 8 }}>
              <Popconfirm
                title="确定删除这个导演世界？"
                onConfirm={() => handleDelete(world.id)}
                okText="确定"
                cancelText="取消"
              >
                <Tooltip title="删除">
                  <Button
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                    style={{ color: 'rgba(255,255,255,0.35)' }}
                    danger
                  />
                </Tooltip>
              </Popconfirm>
            </div>
          </div>
        </Card>
      </Col>
    );
  };

  // 创建弹窗的表单
  const renderCreateForm = () => (
    <>
      <Form.Item
        name="name"
        label="场景名称"
        rules={[{ required: true, message: '请输入导演世界名称' }]}
      >
        <Input
          placeholder="例如：英雄登场、决战天台"
          prefix={<EnvironmentOutlined style={{ color: 'rgba(255,255,255,0.25)' }} />}
        />
      </Form.Item>
      <Form.Item name="description" label="描述">
        <TextArea
          rows={2}
          placeholder="简要描述这个场景设定的内容"
        />
      </Form.Item>
      <Form.Item name="scene_id" label="关联场景 ID">
        <Input placeholder="可选，关联已有场景" />
      </Form.Item>

      <Divider orientation="left" style={{ fontSize: 13, color: 'rgba(255,255,255,0.45)' }}>
        <CameraOutlined /> 相机位置
      </Divider>

      <Row gutter={12}>
        <Col span={8}>
          <Form.Item name="camera_x" label="X" initialValue={0}>
            <InputNumber size="small" style={{ width: '100%' }} step={0.5} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="camera_y" label="Y" initialValue={0}>
            <InputNumber size="small" style={{ width: '100%' }} step={0.5} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item name="camera_z" label="Z" initialValue={5}>
            <InputNumber size="small" style={{ width: '100%' }} step={0.5} />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={12}>
        <Col span={12}>
          <Form.Item name="camera_angle" label="角度" initialValue={0}>
            <InputNumber
              size="small"
              style={{ width: '100%' }}
              min={0}
              max={360}
              addonAfter="°"
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item name="camera_fov" label="视场角" initialValue={60}>
            <InputNumber
              size="small"
              style={{ width: '100%' }}
              min={10}
              max={180}
              addonAfter="°"
            />
          </Form.Item>
        </Col>
      </Row>

      <Divider orientation="left" style={{ fontSize: 13, color: 'rgba(255,255,255,0.45)' }}>
        <TeamOutlined /> 角色阻挡布局
      </Divider>

      <Form.List name="characters">
        {(fields, { add, remove }) => (
          <>
            {fields.map(({ key, name, ...rest }) => (
              <Row gutter={8} key={key} align="middle" style={{ marginBottom: 8 }}>
                <Col flex="auto">
                  <Row gutter={8}>
                    <Col span={8}>
                      <Form.Item {...rest} name={[name, 'name']} noStyle>
                        <Input placeholder="角色名" size="small" />
                      </Form.Item>
                    </Col>
                    <Col span={4}>
                      <Form.Item {...rest} name={[name, 'x']} noStyle initialValue={0}>
                        <InputNumber placeholder="X" size="small" style={{ width: '100%' }} step={0.5} />
                      </Form.Item>
                    </Col>
                    <Col span={4}>
                      <Form.Item {...rest} name={[name, 'y']} noStyle initialValue={0}>
                        <InputNumber placeholder="Y" size="small" style={{ width: '100%' }} step={0.5} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item {...rest} name={[name, 'color']} noStyle initialValue="#4f46e5">
                        <Select
                          size="small"
                          style={{ width: '100%' }}
                          options={[
                            { label: '紫色', value: '#4f46e5' },
                            { label: '蓝色', value: '#2563eb' },
                            { label: '绿色', value: '#059669' },
                            { label: '红色', value: '#dc2626' },
                            { label: '橙色', value: '#ea580c' },
                            { label: '粉色', value: '#db2777' },
                          ]}
                        />
                      </Form.Item>
                    </Col>
                  </Row>
                </Col>
                <Col>
                  <Button
                    type="text"
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => remove(name)}
                    style={{ color: 'rgba(255,255,255,0.35)' }}
                  />
                </Col>
              </Row>
            ))}
            <Button
              type="dashed"
              size="small"
              onClick={() => add()}
              icon={<PlusOutlined />}
              style={{ width: '100%', marginTop: 4 }}
            >
              添加角色
            </Button>
          </>
        )}
      </Form.List>
    </>
  );

  return (
    <div>
      {/* 页面头部 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 10,
                background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 18,
                color: '#fff',
              }}
            >
              <SettingOutlined />
            </div>
            <div>
              <Title level={4} style={{ margin: 0, color: '#fff' }}>
                导演世界
              </Title>
              <Text style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13 }}>
                3GS 虚拟场景编排与变体管理
              </Text>
            </div>
          </div>
        </Col>
        <Col>{projectSelector}</Col>
      </Row>

      {/* 提示信息 */}
      {!selectedProject && (
        <Card
          style={{
            borderRadius: 12,
            border: '1px dashed rgba(124, 58, 237, 0.3)',
            background: 'rgba(30, 27, 75, 0.5)',
            marginBottom: 24,
          }}
          bodyStyle={{ padding: '32px 24px' }}
        >
          <div style={{ textAlign: 'center' }}>
            <EyeOutlined style={{ fontSize: 36, color: 'rgba(124, 58, 237, 0.4)', marginBottom: 12 }} />
            <Title level={5} style={{ color: 'rgba(255,255,255,0.6)', margin: '0 0 4px' }}>
              选择项目开始编排
            </Title>
            <Text style={{ color: 'rgba(255,255,255,0.3)', fontSize: 13 }}>
              选择一个项目，进入导演世界进行场景变体管理与虚拟摄像机布局
            </Text>
          </div>
        </Card>
      )}

      {/* 世界卡片列表 */}
      {selectedProject && (
        <>
          {/* 工具栏 */}
          <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
            <Col>
              <Space>
                <Text style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>
                  共 {worlds.length} 个导演世界
                </Text>
                <Tag
                  color="purple"
                  style={{ borderRadius: 6, border: 'none', fontSize: 11 }}
                >
                  <BranchesOutlined /> 3GS 虚拟场景
                </Tag>
              </Space>
            </Col>
            <Col>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  form.resetFields();
                  setModalVisible(true);
                }}
                style={{
                  background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
                  border: 'none',
                  borderRadius: 8,
                  boxShadow: '0 2px 8px rgba(124, 58, 237, 0.3)',
                }}
              >
                新建导演世界
              </Button>
            </Col>
          </Row>

          {/* 卡片网格 */}
          <Spin spinning={loading}>
            <Row gutter={[16, 16]}>
              {worlds.map(renderWorldCard)}

              {worlds.length === 0 && !loading && (
                <Col span={24}>
                  <Card
                    style={{
                      borderRadius: 12,
                      border: '1px dashed rgba(124, 58, 237, 0.2)',
                      background: 'rgba(30, 27, 75, 0.3)',
                    }}
                    bodyStyle={{ padding: '48px 24px' }}
                  >
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description={
                        <div style={{ textAlign: 'center' }}>
                          <Text style={{ color: 'rgba(255,255,255,0.4)', display: 'block', marginBottom: 8 }}>
                            暂无导演世界
                          </Text>
                          <Text style={{ color: 'rgba(255,255,255,0.25)', fontSize: 12, display: 'block' }}>
                            点击「新建导演世界」开始编排你的第一个场景
                          </Text>
                        </div>
                      }
                    />
                  </Card>
                </Col>
              )}
            </Row>
          </Spin>
        </>
      )}

      {/* 创建弹窗 */}
      <Modal
        title={
          <Space>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 6,
                background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 14,
                color: '#fff',
              }}
            >
              <PlusOutlined />
            </div>
            <span>新建导演世界</span>
          </Space>
        }
        open={modalVisible}
        onOk={handleCreate}
        onCancel={() => setModalVisible(false)}
        width={580}
        okText="创建"
        cancelText="取消"
        okButtonProps={{
          style: {
            background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
            border: 'none',
            borderRadius: 6,
          },
        }}
        destroyOnClose
        style={{ top: 60 }}
        modalRender={node => (
          <div style={{ borderRadius: 12, overflow: 'hidden' }}>
            {node}
          </div>
        )}
      >
        <Form
          form={form}
          layout="vertical"
          style={{ marginTop: 8 }}
        >
          {renderCreateForm()}
        </Form>
      </Modal>
    </div>
  );
};

export default DirectorWorldPage;