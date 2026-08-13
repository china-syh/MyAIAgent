import React, { useEffect, useState } from 'react';
import {
  Card, Tabs, Row, Col, Typography, Space, Button, Table, Tag,
  Modal, Form, Input, Select, message, Empty, Upload, Tooltip,
  Descriptions, Popconfirm, Divider, Badge,
} from 'antd';
import {
  PlusOutlined, FileImageOutlined, SoundOutlined,
  EnvironmentOutlined, ToolOutlined, DeleteOutlined,
  TeamOutlined, ReloadOutlined,
} from '@ant-design/icons';
import { assetApi, projectApi } from '../api/client';
import type { Project, Scene, Prop, Voice, Episode } from '../types';

const { Title, Text } = Typography;
const { TextArea } = Input;

const AssetLibraryPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [props, setProps] = useState<Prop[]>([]);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [modalType, setModalType] = useState<'scene' | 'prop' | 'voice' | 'episode'>('scene');
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('episodes');

  useEffect(() => {
    projectApi.list().then(res => setProjects(Array.isArray(res) ? res : [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedProject) return;
    loadAll();
  }, [selectedProject]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [epRes, scRes, prRes, voRes] = await Promise.all([
        assetApi.episodes.list(selectedProject),
        assetApi.scenes.list(selectedProject),
        assetApi.props.list(selectedProject),
        assetApi.voices.list(selectedProject),
      ]);
      setEpisodes(Array.isArray(epRes) ? epRes : []);
      setScenes(Array.isArray(scRes) ? scRes : []);
      setProps(Array.isArray(prRes) ? prRes : []);
      setVoices(Array.isArray(voRes) ? voRes : []);
    } catch { /* ignore */ }
    setLoading(false);
  };

  const showCreateModal = (type: 'scene' | 'prop' | 'voice' | 'episode') => {
    setModalType(type);
    form.resetFields();
    setModalVisible(true);
  };

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      switch (modalType) {
        case 'episode':
          await assetApi.episodes.create(selectedProject, values);
          message.success('剧集创建成功');
          break;
        case 'scene':
          await assetApi.scenes.create(selectedProject, values);
          message.success('场景创建成功');
          break;
        case 'prop':
          await assetApi.props.create(selectedProject, values);
          message.success('道具创建成功');
          break;
        case 'voice':
          await assetApi.voices.create(selectedProject, values);
          message.success('语音创建成功');
          break;
      }
      setModalVisible(false);
      loadAll();
    } catch (e: any) {
      if (e.message) message.error(e.message);
    }
  };

  const getModalTitle = () => {
    const map = { scene: '创建场景', prop: '创建道具', voice: '创建配音角色', episode: '创建剧集' };
    return map[modalType];
  };

  const renderModalForm = () => {
    switch (modalType) {
      case 'episode':
        return (
          <>
            <Form.Item name="episode_number" label="集数" rules={[{ required: true }]}>
              <Input type="number" min={1} />
            </Form.Item>
            <Form.Item name="title" label="标题" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="summary" label="概要">
              <TextArea rows={3} />
            </Form.Item>
          </>
        );
      case 'scene':
        return (
          <>
            <Form.Item name="name" label="场景名称" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="description" label="描述">
              <TextArea rows={3} />
            </Form.Item>
            <Form.Item name="atmosphere" label="氛围">
              <Select options={[
                { label: '明亮', value: 'bright' }, { label: '阴暗', value: 'dark' },
                { label: '浪漫', value: 'romantic' }, { label: '紧张', value: 'tense' },
                { label: '梦幻', value: 'dreamy' }, { label: '史诗', value: 'epic' },
              ]} />
            </Form.Item>
            <Form.Item name="time_of_day" label="时间段">
              <Select options={[
                { label: '白天', value: 'day' }, { label: '夜晚', value: 'night' },
                { label: '黄昏', value: 'dusk' }, { label: '黎明', value: 'dawn' },
              ]} />
            </Form.Item>
          </>
        );
      case 'prop':
        return (
          <>
            <Form.Item name="name" label="道具名称" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="category" label="分类" initialValue="prop">
              <Select options={[
                { label: '道具', value: 'prop' }, { label: '服装', value: 'costume' },
                { label: '武器', value: 'weapon' }, { label: '载具', value: 'vehicle' },
              ]} />
            </Form.Item>
            <Form.Item name="description" label="描述">
              <TextArea rows={3} />
            </Form.Item>
          </>
        );
      case 'voice':
        return (
          <>
            <Form.Item name="character_name" label="角色名称" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="gender" label="性别" initialValue="neutral">
              <Select options={[
                { label: '中性', value: 'neutral' }, { label: '男', value: 'male' },
                { label: '女', value: 'female' },
              ]} />
            </Form.Item>
            <Form.Item name="style" label="风格" initialValue="natural">
              <Select options={[
                { label: '自然', value: 'natural' }, { label: '情感丰富', value: 'emotional' },
                { label: '戏剧化', value: 'dramatic' },
              ]} />
            </Form.Item>
          </>
        );
    }
  };

  const projectSelector = (
    <Space>
      <Text type="secondary">选择项目：</Text>
      <Select
        style={{ width: 240 }}
        placeholder="选择项目管理资产"
        value={selectedProject || undefined}
        onChange={v => setSelectedProject(v)}
        options={projects.map(p => ({ label: p.name, value: p.id }))}
        allowClear
      />
      <Button icon={<ReloadOutlined />} onClick={loadAll} loading={loading}>刷新</Button>
    </Space>
  );

  const episodeContent = (
    <div>
      <Row justify="space-between" style={{ marginBottom: 16 }}>
        <Col><Text type="secondary">共 {episodes.length} 集</Text></Col>
        <Col>
          {selectedProject && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => showCreateModal('episode')}>
              新增剧集
            </Button>
          )}
        </Col>
      </Row>
      <Row gutter={[16, 16]}>
        {episodes.map(ep => (
          <Col span={8} key={ep.id}>
            <Card
              size="small"
              className="agent-card"
              title={<Space><Badge count={`第${ep.episode_number}集`} style={{ backgroundColor: '#7c3aed' }} /><Text strong>{ep.title || '未命名'}</Text></Space>}
            >
              <Text type="secondary" style={{ fontSize: 13 }}>
                {ep.summary || '暂无概要'}
              </Text>
              {ep.beats && ep.beats.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>剧情节拍：</Text>
                  <Space wrap>
                    {(ep.beats as any[]).map((b: any, i: number) => (
                      <Tag key={i} color="purple">{b.description || `节拍${i + 1}`}</Tag>
                    ))}
                  </Space>
                </div>
              )}
            </Card>
          </Col>
        ))}
        {episodes.length === 0 && !selectedProject && (
          <Col span={24}><Empty description="请先选择项目" /></Col>
        )}
        {episodes.length === 0 && selectedProject && (
          <Col span={24}><Empty description="暂无剧集，点击新增" /></Col>
        )}
      </Row>
    </div>
  );

  const scenesContent = (
    <div>
      <Row justify="space-between" style={{ marginBottom: 16 }}>
        <Col><Text type="secondary">共 {scenes.length} 个场景</Text></Col>
        <Col>
          {selectedProject && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => showCreateModal('scene')}>
              新增场景
            </Button>
          )}
        </Col>
      </Row>
      <Row gutter={[16, 16]}>
        {scenes.map(sc => (
          <Col span={8} key={sc.id}>
            <Card size="small" className="agent-card" title={<Space><EnvironmentOutlined style={{ color: '#7c3aed' }} /><Text strong>{sc.name}</Text></Space>}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="氛围"><Tag>{sc.atmosphere || '未设置'}</Tag></Descriptions.Item>
                <Descriptions.Item label="时间"><Tag>{sc.time_of_day}</Tag></Descriptions.Item>
              </Descriptions>
              {sc.description && <Text type="secondary" style={{ fontSize: 13 }}>{sc.description}</Text>}
            </Card>
          </Col>
        ))}
        {scenes.length === 0 && selectedProject && (
          <Col span={24}><Empty description="暂无场景" /></Col>
        )}
      </Row>
    </div>
  );

  const propsContent = (
    <div>
      <Row justify="space-between" style={{ marginBottom: 16 }}>
        <Col><Text type="secondary">共 {props.length} 个道具</Text></Col>
        <Col>
          {selectedProject && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => showCreateModal('prop')}>
              新增道具
            </Button>
          )}
        </Col>
      </Row>
      <Table
        dataSource={props}
        columns={[
          { title: '名称', dataIndex: 'name', key: 'name' },
          {
            title: '分类', dataIndex: 'category', key: 'category', width: 100,
            render: (v: string) => <Tag>{v}</Tag>,
          },
          { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
        ]}
        rowKey="id"
        size="small"
        locale={{ emptyText: <Empty description="暂无道具" /> }}
      />
    </div>
  );

  const voicesContent = (
    <div>
      <Row justify="space-between" style={{ marginBottom: 16 }}>
        <Col><Text type="secondary">共 {voices.length} 个配音角色</Text></Col>
        <Col>
          {selectedProject && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => showCreateModal('voice')}>
              新增配音
            </Button>
          )}
        </Col>
      </Row>
      <Table
        dataSource={voices}
        columns={[
          { title: '角色', dataIndex: 'character_name', key: 'character_name' },
          {
            title: '性别', dataIndex: 'gender', key: 'gender', width: 80,
            render: (v: string) => v === 'male' ? '男' : v === 'female' ? '女' : '中性',
          },
          {
            title: '风格', dataIndex: 'style', key: 'style', width: 100,
            render: (v: string) => <Tag color="blue">{v}</Tag>,
          },
          {
            title: '状态', dataIndex: 'status', key: 'status', width: 80,
            render: (v: string) => <Badge status={v === 'completed' ? 'success' : 'processing'} text={v === 'completed' ? '已就绪' : '待生成'} />,
          },
        ]}
        rowKey="id"
        size="small"
        locale={{ emptyText: <Empty description="暂无配音" /> }}
      />
    </div>
  );

  const tabItems = [
    { key: 'episodes', label: <Space><TeamOutlined />剧集规划 ({episodes.length})</Space>, children: episodeContent },
    { key: 'scenes', label: <Space><EnvironmentOutlined />场景 ({scenes.length})</Space>, children: scenesContent },
    { key: 'props', label: <Space><ToolOutlined />道具 ({props.length})</Space>, children: propsContent },
    { key: 'voices', label: <Space><SoundOutlined />配音 ({voices.length})</Space>, children: voicesContent },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}><TeamOutlined /> 资产库</Title>
          <Text type="secondary">统一管理角色、场景、道具、配音</Text>
        </Col>
        <Col>{projectSelector}</Col>
      </Row>

      <Card size="small">
        {!selectedProject ? (
          <Empty description="请先选择项目" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
        )}
      </Card>

      <Modal
        title={getModalTitle()}
        open={modalVisible}
        onOk={handleCreate}
        onCancel={() => setModalVisible(false)}
        width={500}
      >
        <Form form={form} layout="vertical">
          {renderModalForm()}
        </Form>
      </Modal>
    </div>
  );
};

export default AssetLibraryPage;