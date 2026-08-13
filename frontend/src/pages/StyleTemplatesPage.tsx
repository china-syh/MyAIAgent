import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Select,
  Modal,
  Form,
  Input,
  Tag,
  ColorPicker,
  Badge,
  Switch,
  Empty,
  Space,
  Tooltip,
  message,
  Typography,
  Popconfirm,
  Divider,
  Spin,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  DeleteOutlined,
  CheckOutlined,
  GlobalOutlined,
  BulbOutlined,
  SmileOutlined,
  AppstoreOutlined,
  BgColorsOutlined,
  MinusCircleOutlined,
} from '@ant-design/icons';
import { styleTemplateApi, projectApi } from '../api/client';
import type { StyleTemplate, Project } from '../types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const LIGHTING_OPTIONS = [
  { label: '自然光', value: 'natural' },
  { label: '柔光', value: 'soft' },
  { label: '强光', value: 'hard' },
  { label: '背光', value: 'backlit' },
  { label: '霓虹', value: 'neon' },
  { label: '月光', value: 'moonlight' },
  { label: '黄昏', value: 'golden_hour' },
  { label: '阴天', value: 'overcast' },
  { label: '舞台光', value: 'spotlight' },
  { label: '烛光', value: 'candlelight' },
];

const MOOD_OPTIONS = [
  { label: '中性', value: 'neutral' },
  { label: '欢乐', value: 'happy' },
  { label: '悲伤', value: 'sad' },
  { label: '紧张', value: 'tense' },
  { label: '神秘', value: 'mysterious' },
  { label: '梦幻', value: 'dreamy' },
  { label: '史诗', value: 'epic' },
  { label: '黑暗', value: 'dark' },
  { label: '浪漫', value: 'romantic' },
  { label: '温馨', value: 'warm' },
  { label: '冷峻', value: 'cold' },
  { label: '复古', value: 'vintage' },
];

const DEFAULT_COLORS = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe'];

const StyleTemplatesPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [templates, setTemplates] = useState<StyleTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [applyModalVisible, setApplyModalVisible] = useState(false);
  const [applyTemplateId, setApplyTemplateId] = useState<string>('');
  const [applyProjectId, setApplyProjectId] = useState<string>('');
  const [applying, setApplying] = useState(false);
  const [createForm] = Form.useForm();

  // 加载项目列表
  useEffect(() => {
    projectApi
      .list()
      .then((res) => setProjects(Array.isArray(res) ? res : []))
      .catch(() => message.error('加载项目列表失败'));
  }, []);

  // 选择项目后加载模板
  useEffect(() => {
    if (!selectedProject) {
      setTemplates([]);
      return;
    }
    loadTemplates();
  }, [selectedProject]);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const res = await styleTemplateApi.list(selectedProject);
      setTemplates(Array.isArray(res) ? res : []);
    } catch {
      message.error('加载风格模板失败');
    }
    setLoading(false);
  };

  // 将 ColorPicker 的 Color 对象转为 hex 字符串
  const toHexString = (c: any): string => {
    if (typeof c === 'string') return c;
    if (c?.toHexString) return c.toHexString();
    return '#000000';
  };

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();

      const colorPalette: string[] = Array.isArray(values.color_palette)
        ? values.color_palette.map(toHexString)
        : [];

      let styleParams: Record<string, unknown> = {};
      if (values.style_params) {
        try {
          styleParams = JSON.parse(values.style_params);
        } catch {
          message.error('风格参数 JSON 格式不正确');
          return;
        }
      }

      const payload = {
        name: values.name,
        description: values.description || '',
        reference_image: values.reference_image || '',
        color_palette: colorPalette,
        lighting: values.lighting || 'natural',
        mood: values.mood || 'neutral',
        style_params: styleParams,
        project_id: selectedProject,
        is_global: values.is_global ?? false,
      };

      await styleTemplateApi.create(payload);
      message.success('风格模板创建成功');
      setCreateModalVisible(false);
      createForm.resetFields();
      loadTemplates();
    } catch (e: any) {
      if (e.message) message.error(e.message);
    }
  };

  const handleApply = async () => {
    if (!applyTemplateId || !applyProjectId) {
      message.warning('请选择目标项目');
      return;
    }
    setApplying(true);
    try {
      await styleTemplateApi.apply(applyTemplateId, { project_id: applyProjectId });
      message.success('模板已成功应用到项目');
      setApplyModalVisible(false);
      setApplyTemplateId('');
      setApplyProjectId('');
    } catch (e: any) {
      if (e.message) message.error(e.message);
    }
    setApplying(false);
  };

  const handleDelete = async (templateId: string) => {
    try {
      await styleTemplateApi.delete(templateId);
      message.success('模板已删除');
      loadTemplates();
    } catch (e: any) {
      if (e.message) message.error(e.message);
    }
  };

  const showApplyModal = (templateId: string) => {
    setApplyTemplateId(templateId);
    setApplyProjectId('');
    setApplyModalVisible(true);
  };

  /** 渲染色板彩色圆点 */
  const renderColorPalette = (colors: string[]) => {
    if (!colors || colors.length === 0) {
      return <Text type="secondary" style={{ fontSize: 12 }}>无色板</Text>;
    }
    return (
      <Space size={4} wrap>
        {colors.map((color, index) => (
          <Tooltip key={index} title={color}>
            <div
              style={{
                width: 22,
                height: 22,
                borderRadius: '50%',
                backgroundColor: color,
                border: '1px solid rgba(0,0,0,0.1)',
                display: 'inline-block',
                cursor: 'pointer',
                boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
                transition: 'transform 0.2s',
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.transform = 'scale(1.2)';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.transform = 'scale(1)';
              }}
            />
          </Tooltip>
        ))}
      </Space>
    );
  };

  /** 渲染模板卡片封面区域（参考图或渐变占位） */
  const renderCardCover = (template: StyleTemplate) => {
    const hasColors =
      template.color_palette && template.color_palette.length > 0;

    if (template.reference_image) {
      return (
        <div
          style={{
            height: 170,
            overflow: 'hidden',
            background: '#f0f0f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <img
            src={template.reference_image}
            alt={template.name}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        </div>
      );
    }

    // 无参考图时用色板生成渐变背景
    if (hasColors) {
      const gradient = template.color_palette
        .map((c, i) => `${c} ${(i / template.color_palette.length) * 100}%`)
        .join(', ');
      return (
        <div
          style={{
            height: 170,
            background: `linear-gradient(135deg, ${gradient})`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <BgColorsOutlined style={{ fontSize: 52, color: 'rgba(255,255,255,0.7)' }} />
        </div>
      );
    }

    // 默认渐变
    return (
      <div
        style={{
          height: 170,
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <BgColorsOutlined style={{ fontSize: 52, color: 'rgba(255,255,255,0.6)' }} />
      </div>
    );
  };

  const projectSelector = (
    <Space>
      <Text type="secondary">选择项目：</Text>
      <Select
        style={{ width: 240 }}
        placeholder="选择项目查看风格模板"
        value={selectedProject || undefined}
        onChange={(v) => setSelectedProject(v)}
        options={projects.map((p) => ({ label: p.name, value: p.id }))}
        allowClear
      />
      <Tooltip title="刷新模板列表">
        <Button
          icon={<ReloadOutlined />}
          onClick={loadTemplates}
          loading={loading}
        >
          刷新
        </Button>
      </Tooltip>
    </Space>
  );

  return (
    <div>
      {/* 页面头部 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <BgColorsOutlined style={{ marginRight: 8 }} />
            视觉风格模板
          </Title>
          <Text type="secondary">
            管理和复用漫画视觉风格模板 — 一键应用到项目
          </Text>
        </Col>
        <Col>{projectSelector}</Col>
      </Row>

      {/* 工具栏 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Text type="secondary">
            共 <Badge count={templates.length} style={{ backgroundColor: '#7c3aed' }} /> 个模板
          </Text>
        </Col>
        <Col>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              createForm.resetFields();
              createForm.setFieldsValue({
                color_palette: DEFAULT_COLORS,
                lighting: 'natural',
                mood: 'neutral',
                is_global: false,
              });
              setCreateModalVisible(true);
            }}
          >
            新建模板
          </Button>
        </Col>
      </Row>

      {/* 模板卡片网格 */}
      {!selectedProject ? (
        <Card>
          <Empty
            description="请先选择一个项目"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </Card>
      ) : loading ? (
        <div style={{ textAlign: 'center', padding: 80 }}>
          <Spin size="large" tip="加载中..." />
        </div>
      ) : templates.length === 0 ? (
        <Card>
          <Empty description="暂无风格模板，点击右上角「新建模板」开始创建">
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                createForm.resetFields();
                createForm.setFieldsValue({
                  color_palette: DEFAULT_COLORS,
                  lighting: 'natural',
                  mood: 'neutral',
                  is_global: false,
                });
                setCreateModalVisible(true);
              }}
            >
              新建模板
            </Button>
          </Empty>
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          {templates.map((template) => (
            <Col xs={24} sm={12} md={8} lg={6} key={template.id}>
              <Card
                hoverable
                className="style-template-card"
                style={{
                  borderRadius: 12,
                  overflow: 'hidden',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                }}
                cover={renderCardCover(template)}
                actions={[
                  <Tooltip title="将此模板应用到其他项目" key="apply">
                    <Button
                      type="link"
                      icon={<CheckOutlined />}
                      onClick={() => showApplyModal(template.id)}
                      style={{ color: '#52c41a' }}
                    >
                      应用
                    </Button>
                  </Tooltip>,
                  <Popconfirm
                    key="delete"
                    title="确定删除此模板？"
                    description="删除后无法恢复，请谨慎操作。"
                    onConfirm={() => handleDelete(template.id)}
                    okText="确认删除"
                    cancelText="取消"
                  >
                    <Button type="link" danger icon={<DeleteOutlined />}>
                      删除
                    </Button>
                  </Popconfirm>,
                ]}
              >
                <Card.Meta
                  title={
                    <Space align="center" style={{ marginBottom: 4 }}>
                      <Text strong ellipsis style={{ maxWidth: 140, fontSize: 15 }}>
                        {template.name}
                      </Text>
                      {template.is_global && (
                        <Tag
                          icon={<GlobalOutlined />}
                          color="blue"
                          style={{ margin: 0, fontSize: 11 }}
                        >
                          全局
                        </Tag>
                      )}
                    </Space>
                  }
                  description={
                    <div>
                      {/* 描述 */}
                      <Paragraph
                        ellipsis={{ rows: 2 }}
                        style={{ marginBottom: 8, fontSize: 12, color: '#666' }}
                      >
                        {template.description || '暂无描述'}
                      </Paragraph>

                      <Divider style={{ margin: '8px 0' }} />

                      {/* 色板 */}
                      <div style={{ marginBottom: 8 }}>
                        <Space align="center" style={{ marginBottom: 4 }}>
                          <BgColorsOutlined style={{ fontSize: 12, color: '#888' }} />
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            色板
                          </Text>
                        </Space>
                        <div style={{ marginTop: 2 }}>
                          {renderColorPalette(template.color_palette)}
                        </div>
                      </div>

                      {/* 光照 + 情绪 */}
                      <Space size={6} wrap>
                        <Tooltip title={`光照风格: ${template.lighting || '未设置'}`}>
                          <Tag
                            icon={<BulbOutlined />}
                            color="orange"
                            style={{ borderRadius: 8, fontSize: 11 }}
                          >
                            {template.lighting || '未设置'}
                          </Tag>
                        </Tooltip>
                        <Tooltip title={`情绪氛围: ${template.mood || '未设置'}`}>
                          <Tag
                            icon={<SmileOutlined />}
                            color="purple"
                            style={{ borderRadius: 8, fontSize: 11 }}
                          >
                            {template.mood || '未设置'}
                          </Tag>
                        </Tooltip>
                      </Space>

                      {/* style_params 预览 */}
                      {template.style_params &&
                        Object.keys(template.style_params).length > 0 && (
                          <div style={{ marginTop: 8 }}>
                            <Space align="center" style={{ marginBottom: 2 }}>
                              <AppstoreOutlined
                                style={{ fontSize: 12, color: '#888' }}
                              />
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                参数
                              </Text>
                            </Space>
                            <div style={{ marginTop: 2 }}>
                              {Object.entries(template.style_params)
                                .slice(0, 3)
                                .map(([key, value]) => (
                                  <Tag
                                    key={key}
                                    style={{
                                      fontSize: 10,
                                      marginBottom: 2,
                                      borderRadius: 6,
                                    }}
                                  >
                                    {key}: {String(value).substring(0, 12)}
                                  </Tag>
                                ))}
                              {Object.keys(template.style_params).length > 3 && (
                                <Tag style={{ fontSize: 10, borderRadius: 6 }}>
                                  +{Object.keys(template.style_params).length - 3}
                                </Tag>
                              )}
                            </div>
                          </div>
                        )}
                    </div>
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* ========== 创建模板模态框 ========== */}
      <Modal
        title={
          <Space>
            <BgColorsOutlined />
            <span>创建风格模板</span>
          </Space>
        }
        open={createModalVisible}
        onOk={handleCreate}
        onCancel={() => setCreateModalVisible(false)}
        width={680}
        okText="创建"
        cancelText="取消"
        destroyOnClose
      >
        <Form
          form={createForm}
          layout="vertical"
          initialValues={{
            color_palette: DEFAULT_COLORS,
            lighting: 'natural',
            mood: 'neutral',
            is_global: false,
          }}
          style={{ marginTop: 8 }}
        >
          <Form.Item
            name="name"
            label="模板名称"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input
              placeholder="例如：梦幻少女风、暗黑武士风"
              prefix={<BgColorsOutlined style={{ color: '#bfbfbf' }} />}
            />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea
              rows={2}
              placeholder="描述这个模板的视觉风格特点，便于团队理解和使用"
            />
          </Form.Item>

          <Form.Item name="reference_image" label="参考图片 URL">
            <Input placeholder="https://example.com/style-reference.jpg" />
          </Form.Item>

          {/* 色板 - 使用 Form.List 支持多色 */}
          <Form.List name="color_palette">
            {(fields, { add, remove }) => (
              <div>
                <Form.Item label="色板">
                  <Space align="center" style={{ marginBottom: 8 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      添加主题色，鼠标悬停可预览色值
                    </Text>
                    <Button
                      type="dashed"
                      size="small"
                      icon={<PlusOutlined />}
                      onClick={() => add('#667eea')}
                    >
                      添加颜色
                    </Button>
                  </Space>
                </Form.Item>
                <Row gutter={[8, 8]}>
                  {fields.map(({ key, name, ...restField }, index) => (
                    <Col key={key} style={{ marginBottom: 8 }}>
                      <Form.Item
                        {...restField}
                        name={[name]}
                        rules={[{ required: true, message: '请选择颜色' }]}
                        style={{ margin: 0 }}
                        getValueFromEvent={(color: any) => color}
                      >
                        <ColorPicker
                          showText
                          style={{ width: 100 }}
                          size="small"
                        />
                      </Form.Item>
                      {fields.length > 1 && (
                        <Button
                          type="text"
                          danger
                          size="small"
                          icon={<MinusCircleOutlined />}
                          style={{
                            position: 'absolute',
                            top: -6,
                            right: -6,
                            zIndex: 1,
                            minWidth: 0,
                            width: 18,
                            height: 18,
                            borderRadius: '50%',
                            background: '#fff',
                            boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
                          }}
                          onClick={() => remove(name)}
                        />
                      )}
                    </Col>
                  ))}
                </Row>
              </div>
            )}
          </Form.List>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="lighting" label="光照风格">
                <Select options={LIGHTING_OPTIONS} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="mood" label="情绪氛围">
                <Select options={MOOD_OPTIONS} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="style_params" label="风格参数 (JSON)">
            <TextArea
              rows={4}
              placeholder={`{\n  "style": "anime",\n  "line_weight": 1.2,\n  "color_saturation": 0.8\n}`}
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>

          <Form.Item
            name="is_global"
            label="全局模板"
            valuePropName="checked"
          >
            <Switch
              checkedChildren={<GlobalOutlined />}
              unCheckedChildren={<GlobalOutlined />}
            />
          </Form.Item>
          <Text type="secondary" style={{ fontSize: 12 }}>
            开启后，此模板将作为全局模板在所有项目中可见
          </Text>
        </Form>
      </Modal>

      {/* ========== 应用模板模态框 ========== */}
      <Modal
        title={
          <Space>
            <CheckOutlined style={{ color: '#52c41a' }} />
            <span>应用模板到项目</span>
          </Space>
        }
        open={applyModalVisible}
        onOk={handleApply}
        onCancel={() => {
          setApplyModalVisible(false);
          setApplyProjectId('');
        }}
        confirmLoading={applying}
        okText="应用"
        cancelText="取消"
        destroyOnClose
      >
        <div style={{ padding: '16px 0' }}>
          <Paragraph>
            选择要将此模板应用到的目标项目。当前项目的风格参数将被模板覆盖。
          </Paragraph>
          <div style={{ marginTop: 16 }}>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>
              目标项目
            </Text>
            <Select
              style={{ width: '100%' }}
              placeholder="请选择目标项目"
              value={applyProjectId || undefined}
              onChange={(v) => setApplyProjectId(v)}
              options={projects
                .filter((p) => p.id !== selectedProject)
                .map((p) => ({ label: p.name, value: p.id }))}
              notFoundContent={
                <Empty
                  description="没有其他可选项目"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              }
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default StyleTemplatesPage;