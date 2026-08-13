import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Card,
  Select,
  Button,
  Modal,
  Form,
  Input,
  Slider,
  Tag,
  Badge,
  Empty,
  Table,
  Typography,
  Space,
  Spin,
  message,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  DeleteOutlined,
  ApartmentOutlined,
  TeamOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { storyGraphApi, projectApi, characterApi } from '../api/client';
import type { Character, Project, StoryRelation } from '../types';

const { Title, Text } = Typography;
const { Option } = Select;

// ============ 常量 ============

const CHARACTER_COLORS = [
  '#7c3aed', '#1890ff', '#52c41a', '#fa8c16', '#eb2f96',
  '#13c2c2', '#faad14', '#f5222d', '#722ed1', '#2f54eb',
  '#a0d911', '#fa541c', '#1d39c4', '#c41d7f', '#08979c',
];

const RELATION_TYPE_COLORS: Record<string, string> = {
  family: '#52c41a',
  friend: '#1890ff',
  enemy: '#f5222d',
  love: '#eb2f96',
  rival: '#fa8c16',
  mentor: '#722ed1',
  partner: '#13c2c2',
  acquaintance: '#8c8c8c',
};

const RELATION_TYPE_LABELS: Record<string, string> = {
  family: '家族',
  friend: '朋友',
  enemy: '敌人',
  love: '恋爱',
  rival: '对手',
  mentor: '师徒',
  partner: '搭档',
  acquaintance: '相识',
};

const RELATION_TYPES = Object.keys(RELATION_TYPE_LABELS);

// ============ 工具函数 ============

function getCharacterColor(index: number): string {
  return CHARACTER_COLORS[index % CHARACTER_COLORS.length];
}

function getRelationshipTypeColor(type: string): string {
  return RELATION_TYPE_COLORS[type] || '#8c8c8c';
}

function getRelationshipTypeLabel(type: string): string {
  return RELATION_TYPE_LABELS[type] || type;
}

interface NodePosition {
  x: number;
  y: number;
  character: Character;
  color: string;
}

function computeCircularLayout(
  characters: Character[],
  centerX: number,
  centerY: number,
  radius: number,
): NodePosition[] {
  if (characters.length === 0) return [];
  return characters.map((character, index) => {
    const angle = (2 * Math.PI * index) / characters.length - Math.PI / 2;
    return {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
      character,
      color: getCharacterColor(index),
    };
  });
}

function getCharacterById(
  nodes: NodePosition[],
  id: string,
): NodePosition | undefined {
  return nodes.find((n) => n.character.id === id);
}

// ============ 主组件 ============

const StoryGraphPage: React.FC = () => {
  // ===== 状态 =====
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | undefined>(undefined);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [relationships, setRelationships] = useState<StoryRelation[]>([]);
  const [loading, setLoading] = useState(false);
  const [graphLoading, setGraphLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [adding, setAdding] = useState(false);
  const [hoveredRelation, setHoveredRelation] = useState<string | null>(null);
  const [form] = Form.useForm();

  const SVG_WIDTH = 700;
  const SVG_HEIGHT = 500;
  const CENTER_X = SVG_WIDTH / 2;
  const CENTER_Y = SVG_HEIGHT / 2;
  const RADIUS = 180;

  // ===== 加载项目列表 =====
  const loadProjects = useCallback(async () => {
    setLoading(true);
    try {
      const data = await projectApi.list();
      // 兼容可能返回 { projects: [...] } 或直接数组
      const list = Array.isArray(data) ? data : data?.projects ?? [];
      setProjects(list);
    } catch (err: any) {
      message.error('加载项目列表失败: ' + (err.message || ''));
    } finally {
      setLoading(false);
    }
  }, []);

  // ===== 加载角色和关系 =====
  const loadGraphData = useCallback(async (projectId: string) => {
    if (!projectId) return;
    setGraphLoading(true);
    try {
      const [charData, relData] = await Promise.all([
        characterApi.list(projectId),
        storyGraphApi.list(projectId),
      ]);
      setCharacters(Array.isArray(charData) ? charData : charData?.characters ?? []);
      setRelationships(Array.isArray(relData) ? relData : relData?.relations ?? []);
    } catch (err: any) {
      message.error('加载图谱数据失败: ' + (err.message || ''));
    } finally {
      setGraphLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    if (selectedProjectId) {
      loadGraphData(selectedProjectId);
    } else {
      setCharacters([]);
      setRelationships([]);
    }
  }, [selectedProjectId, loadGraphData]);

  // ===== 计算布局 =====
  const nodes = useMemo(
    () => computeCircularLayout(characters, CENTER_X, CENTER_Y, RADIUS),
    [characters, CENTER_X, CENTER_Y, RADIUS],
  );

  const nodeMap = useMemo(() => {
    const map = new Map<string, NodePosition>();
    nodes.forEach((n) => map.set(n.character.id, n));
    return map;
  }, [nodes]);

  // ===== 添加关系 =====
  const handleAddRelation = async () => {
    try {
      const values = await form.validateFields();
      setAdding(true);
      const data = {
        character_a_id: values.character_a_id,
        character_b_id: values.character_b_id,
        relationship_type: values.relationship_type,
        strength: values.strength ?? 5,
        description: values.description ?? '',
      };
      await storyGraphApi.create(selectedProjectId!, data);
      message.success('关系添加成功');
      setModalVisible(false);
      form.resetFields();
      if (selectedProjectId) loadGraphData(selectedProjectId);
    } catch (err: any) {
      if (err.errorFields) return; // 表单验证错误
      message.error('添加关系失败: ' + (err.message || ''));
    } finally {
      setAdding(false);
    }
  };

  // ===== 删除关系 =====
  const handleDeleteRelation = async (relationId: string) => {
    try {
      await storyGraphApi.delete(selectedProjectId!, relationId);
      message.success('关系已删除');
      if (selectedProjectId) loadGraphData(selectedProjectId);
    } catch (err: any) {
      message.error('删除关系失败: ' + (err.message || ''));
    }
  };

  // ===== 关系表格列 =====
  const relationColumns = [
    {
      title: '角色 A',
      dataIndex: 'character_a_id',
      key: 'character_a_id',
      render: (id: string) => {
        const ch = characters.find((c) => c.id === id);
        return ch ? ch.name : id;
      },
    },
    {
      title: '角色 B',
      dataIndex: 'character_b_id',
      key: 'character_b_id',
      render: (id: string) => {
        const ch = characters.find((c) => c.id === id);
        return ch ? ch.name : id;
      },
    },
    {
      title: '关系类型',
      dataIndex: 'relationship_type',
      key: 'relationship_type',
      render: (type: string) => (
        <Tag color={getRelationshipTypeColor(type)}>
          {getRelationshipTypeLabel(type)}
        </Tag>
      ),
    },
    {
      title: '强度',
      dataIndex: 'strength',
      key: 'strength',
      render: (val: number) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div
            style={{
              width: 60,
              height: 6,
              borderRadius: 3,
              background: '#f0f0f0',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                width: `${(val / 10) * 100}%`,
                height: '100%',
                borderRadius: 3,
                background: val > 7 ? '#52c41a' : val > 4 ? '#fa8c16' : '#f5222d',
              }}
            />
          </div>
          <Text type="secondary" style={{ fontSize: 12 }}>{val}</Text>
        </div>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: unknown, record: StoryRelation) => (
        <Popconfirm
          title="确认删除此关系？"
          onConfirm={() => handleDeleteRelation(record.id)}
          okText="确认"
          cancelText="取消"
        >
          <Button type="link" danger icon={<DeleteOutlined />} size="small" />
        </Popconfirm>
      ),
    },
  ];

  // ===== 渲染 SVG 图谱 =====
  const renderGraph = () => {
    if (characters.length === 0) {
      return (
        <div
          style={{
            height: SVG_HEIGHT,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Empty description="暂无角色数据，请先添加角色" />
        </div>
      );
    }

    return (
      <svg
        width="100%"
        height={SVG_HEIGHT}
        viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
        style={{ display: 'block' }}
      >
        {/* 背景网格装饰 */}
        <defs>
          <pattern
            id="grid-pattern"
            width={40}
            height={40}
            patternUnits="userSpaceOnUse"
          >
            <circle cx={20} cy={20} r={1} fill="#e8e8e8" />
          </pattern>
          <filter id="node-shadow">
            <feDropShadow dx={0} dy={2} stdDeviation={3} floodOpacity={0.15} />
          </filter>
          <filter id="glow">
            <feGaussianBlur stdDeviation={4} result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <rect width={SVG_WIDTH} height={SVG_HEIGHT} fill="url(#grid-pattern)" />

        {/* 关系连线 */}
        {relationships.map((rel) => {
          const nodeA = nodeMap.get(rel.character_a_id);
          const nodeB = nodeMap.get(rel.character_b_id);
          if (!nodeA || !nodeB) return null;

          const color = getRelationshipTypeColor(rel.relationship_type);
          const strokeWidth = 1 + (rel.strength / 10) * 4;
          const isHovered = hoveredRelation === rel.id;

          // 计算箭头
          const dx = nodeB.x - nodeA.x;
          const dy = nodeB.y - nodeA.y;
          const angle = Math.atan2(dy, dx);
          const nodeRadius = 28;
          const arrowLen = 10;
          const startX = nodeA.x + nodeRadius * Math.cos(angle);
          const startY = nodeA.y + nodeRadius * Math.sin(angle);
          const endX = nodeB.x - nodeRadius * Math.cos(angle);
          const endY = nodeB.y - nodeRadius * Math.sin(angle);

          const midX = (startX + endX) / 2;
          const midY = (startY + endY) / 2;

          // 标签偏移
          const perpAngle = angle + Math.PI / 2;
          const labelOffset = 12;
          const labelX = midX + labelOffset * Math.cos(perpAngle);
          const labelY = midY + labelOffset * Math.sin(perpAngle);

          return (
            <g
              key={rel.id}
              onMouseEnter={() => setHoveredRelation(rel.id)}
              onMouseLeave={() => setHoveredRelation(null)}
              style={{ cursor: 'pointer' }}
            >
              {/* 发光效果线（hover） */}
              {isHovered && (
                <line
                  x1={startX}
                  y1={startY}
                  x2={endX}
                  y2={endY}
                  stroke={color}
                  strokeWidth={strokeWidth + 4}
                  opacity={0.2}
                  filter="url(#glow)"
                />
              )}
              {/* 连线 */}
              <line
                x1={startX}
                y1={startY}
                x2={endX}
                y2={endY}
                stroke={color}
                strokeWidth={strokeWidth}
                opacity={isHovered ? 1 : 0.7}
                strokeLinecap="round"
              />
              {/* 箭头 */}
              <polygon
                points={`${endX},${endY} ${endX - arrowLen * Math.cos(angle - 0.4)},${endY - arrowLen * Math.sin(angle - 0.4)} ${endX - arrowLen * Math.cos(angle + 0.4)},${endY - arrowLen * Math.sin(angle + 0.4)}`}
                fill={color}
                opacity={isHovered ? 1 : 0.7}
              />
              {/* 关系标签 */}
              <g>
                <rect
                  x={labelX - 28}
                  y={labelY - 9}
                  width={56}
                  height={18}
                  rx={9}
                  fill="white"
                  stroke={color}
                  strokeWidth={1}
                  opacity={0.95}
                />
                <text
                  x={labelX}
                  y={labelY + 4}
                  textAnchor="middle"
                  fill={color}
                  fontSize={11}
                  fontWeight={500}
                >
                  {getRelationshipTypeLabel(rel.relationship_type)}
                </text>
              </g>
            </g>
          );
        })}

        {/* 角色节点 */}
        {nodes.map((node) => {
          const isHovered = relationships.some(
            (r) =>
              hoveredRelation === r.id &&
              (r.character_a_id === node.character.id ||
                r.character_b_id === node.character.id),
          );

          return (
            <g
              key={node.character.id}
              style={{ cursor: 'pointer' }}
              filter="url(#node-shadow)"
            >
              {/* 外圈光晕 */}
              <circle
                cx={node.x}
                cy={node.y}
                r={32}
                fill={node.color}
                opacity={0.08}
              />
              {/* 节点圆 */}
              <circle
                cx={node.x}
                cy={node.y}
                r={28}
                fill={node.color}
                stroke="white"
                strokeWidth={3}
                opacity={isHovered ? 1 : 0.9}
              />
              {/* 首字母 */}
              <text
                x={node.x}
                y={node.y + 1}
                textAnchor="middle"
                dominantBaseline="central"
                fill="white"
                fontSize={16}
                fontWeight={700}
              >
                {node.character.name.charAt(0)}
              </text>
              {/* 角色名 */}
              <text
                x={node.x}
                y={node.y + 42}
                textAnchor="middle"
                fill="#333"
                fontSize={12}
                fontWeight={500}
              >
                {node.character.name}
              </text>
              {/* 角色身份 */}
              <text
                x={node.x}
                y={node.y + 56}
                textAnchor="middle"
                fill="#999"
                fontSize={10}
              >
                {node.character.role || ''}
              </text>
            </g>
          );
        })}
      </svg>
    );
  };

  // ===== 渲染 =====
  return (
    <div style={{ padding: 24 }}>
      {/* 头部 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 24,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <ApartmentOutlined style={{ fontSize: 24, color: '#7c3aed' }} />
          <Title level={4} style={{ margin: 0 }}>
            故事图谱
          </Title>
        </div>
        <Space>
          <Select
            placeholder="选择项目"
            style={{ width: 260 }}
            value={selectedProjectId}
            onChange={(val) => setSelectedProjectId(val)}
            loading={loading}
            allowClear
            showSearch
            optionFilterProp="children"
          >
            {projects.map((p) => (
              <Option key={p.id} value={p.id}>
                {p.name}
              </Option>
            ))}
          </Select>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => selectedProjectId && loadGraphData(selectedProjectId)}
            disabled={!selectedProjectId}
          >
            刷新
          </Button>
        </Space>
      </div>

      {!selectedProjectId ? (
        <Card>
          <Empty description="请选择一个项目以查看故事图谱" />
        </Card>
      ) : (
        <Spin spinning={graphLoading}>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {/* 左侧 - 图谱可视化 */}
            <div style={{ flex: '1 1 640px', minWidth: 0 }}>
              <Card
                title={
                  <Space>
                    <TeamOutlined />
                    <span>角色关系图谱</span>
                    <Badge
                      count={characters.length}
                      style={{ backgroundColor: '#7c3aed' }}
                      overflowCount={99}
                      showZero
                    />
                    <Text type="secondary" style={{ fontSize: 13, fontWeight: 400 }}>
                      角色
                    </Text>
                    <Badge
                      count={relationships.length}
                      style={{ backgroundColor: '#1890ff' }}
                      overflowCount={999}
                      showZero
                    />
                    <Text type="secondary" style={{ fontSize: 13, fontWeight: 400 }}>
                      关系
                    </Text>
                  </Space>
                }
                extra={
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => {
                      form.resetFields();
                      setModalVisible(true);
                    }}
                    disabled={characters.length < 2}
                  >
                    添加关系
                  </Button>
                }
                bodyStyle={{ padding: 0, overflow: 'hidden' }}
              >
                <div
                  style={{
                    background: '#fafafa',
                    borderBottom: '1px solid #f0f0f0',
                    padding: '8px 16px',
                    display: 'flex',
                    gap: 16,
                    flexWrap: 'wrap',
                  }}
                >
                  {RELATION_TYPES.map((type) => (
                    <Tag
                      key={type}
                      color={getRelationshipTypeColor(type)}
                      style={{ margin: 0 }}
                    >
                      {getRelationshipTypeLabel(type)}
                    </Tag>
                  ))}
                </div>
                {renderGraph()}
              </Card>
            </div>

            {/* 右侧 - 关系列表 */}
            <div style={{ flex: '1 1 360px', minWidth: 300 }}>
              <Card
                title={
                  <Space>
                    <LinkOutlined />
                    <span>关系列表</span>
                  </Space>
                }
              >
                {relationships.length === 0 ? (
                  <Empty description="暂无关系数据">
                    {characters.length >= 2 && (
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => {
                          form.resetFields();
                          setModalVisible(true);
                        }}
                      >
                        添加第一条关系
                      </Button>
                    )}
                    {characters.length < 2 && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        至少需要 2 个角色才能创建关系
                      </Text>
                    )}
                  </Empty>
                ) : (
                  <Table
                    dataSource={relationships}
                    columns={relationColumns}
                    rowKey="id"
                    size="small"
                    pagination={{ pageSize: 5, size: 'small' }}
                    onRow={(record) => ({
                      onMouseEnter: () => setHoveredRelation(record.id),
                      onMouseLeave: () => setHoveredRelation(null),
                      style: {
                        cursor: 'pointer',
                        background:
                          hoveredRelation === record.id
                            ? 'rgba(124, 58, 237, 0.04)'
                            : undefined,
                        transition: 'background 0.2s',
                      },
                    })}
                  />
                )}
              </Card>
            </div>
          </div>
        </Spin>
      )}

      {/* ===== 添加关系弹窗 ===== */}
      <Modal
        title={
          <Space>
            <PlusOutlined style={{ color: '#7c3aed' }} />
            <span>添加角色关系</span>
          </Space>
        }
        open={modalVisible}
        onOk={handleAddRelation}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        confirmLoading={adding}
        okText="添加"
        cancelText="取消"
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ strength: 5 }}
          style={{ marginTop: 16 }}
        >
          <Form.Item
            name="character_a_id"
            label="角色 A"
            rules={[{ required: true, message: '请选择角色 A' }]}
          >
            <Select placeholder="选择角色 A" showSearch optionFilterProp="children">
              {characters.map((ch) => (
                <Option key={ch.id} value={ch.id}>
                  <Space>
                    <span
                      style={{
                        display: 'inline-block',
                        width: 10,
                        height: 10,
                        borderRadius: '50%',
                        background: getCharacterColor(
                          characters.findIndex((c) => c.id === ch.id),
                        ),
                      }}
                    />
                    {ch.name}
                    {ch.role ? (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        ({ch.role})
                      </Text>
                    ) : null}
                  </Space>
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="character_b_id"
            label="角色 B"
            rules={[{ required: true, message: '请选择角色 B' }]}
          >
            <Select placeholder="选择角色 B" showSearch optionFilterProp="children">
              {characters.map((ch) => (
                <Option key={ch.id} value={ch.id}>
                  <Space>
                    <span
                      style={{
                        display: 'inline-block',
                        width: 10,
                        height: 10,
                        borderRadius: '50%',
                        background: getCharacterColor(
                          characters.findIndex((c) => c.id === ch.id),
                        ),
                      }}
                    />
                    {ch.name}
                    {ch.role ? (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        ({ch.role})
                      </Text>
                    ) : null}
                  </Space>
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="relationship_type"
            label="关系类型"
            rules={[{ required: true, message: '请选择关系类型' }]}
          >
            <Select placeholder="选择关系类型">
              {RELATION_TYPES.map((type) => (
                <Option key={type} value={type}>
                  <Tag color={getRelationshipTypeColor(type)}>
                    {getRelationshipTypeLabel(type)}
                  </Tag>
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="strength"
            label="关系强度"
            extra="数值越大表示关系越紧密"
          >
            <Slider
              min={1}
              max={10}
              marks={{
                1: '1',
                3: '3',
                5: '5',
                7: '7',
                10: '10',
              }}
              trackStyle={{
                background:
                  'linear-gradient(90deg, #f5222d, #fa8c16, #52c41a)',
              }}
            />
          </Form.Item>

          <Form.Item name="description" label="关系描述">
            <Input.TextArea
              placeholder="例如：青梅竹马，从小一起长大的好友"
              rows={3}
              maxLength={200}
              showCount
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default StoryGraphPage;