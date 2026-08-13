import React, { useEffect, useState, useCallback } from 'react';
import {
  Card, Select, Button, Input, Typography, Row, Col, Space, Tag,
  Descriptions, Table, Tabs, message, Empty, Alert, Tooltip, Spin,
} from 'antd';
import {
  BookOutlined, TeamOutlined, FileTextOutlined,
  GlobalOutlined, ThunderboltOutlined, ReloadOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import { novelApi, projectApi } from '../api/client';
import type { Project } from '../types';

const { Title, Text } = Typography;
const { TextArea } = Input;

/* ========== 解析结果类型定义 ========== */

interface ParsedCharacter {
  name: string;
  role: string;
  age?: string;
  gender?: string;
  personality?: string;
  appearance?: string;
  background?: string;
}

interface ParsedChapter {
  title: string;
  summary?: string;
  order?: number;
}

interface ParsedTheme {
  name: string;
  description?: string;
  keywords?: string[];
}

interface ParsedWorldSetting {
  name?: string;
  time_period?: string;
  geography?: string;
  magic_system?: string;
  technology_level?: string;
  culture?: string;
  description?: string;
}

interface NovelParseResult {
  characters: ParsedCharacter[];
  chapters: ParsedChapter[];
  themes: ParsedTheme[];
  world_setting: ParsedWorldSetting;
  raw?: string;
}

/* ========== 默认空结果 ========== */

const EMPTY_RESULT: NovelParseResult = {
  characters: [],
  chapters: [],
  themes: [],
  world_setting: {},
};

const NovelParserPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [content, setContent] = useState('');
  const [parsing, setParsing] = useState(false);
  const [result, setResult] = useState<NovelParseResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  /* ---- 加载项目列表 ---- */

  useEffect(() => {
    projectApi
      .list()
      .then((res) => setProjects(Array.isArray(res) ? res : []))
      .catch(() => {});
  }, []);

  /* ---- 解析小说 ---- */

  const handleParse = useCallback(async () => {
    if (!selectedProject) {
      message.warning('请先选择项目');
      return;
    }
    if (!content.trim()) {
      message.warning('请输入小说内容');
      return;
    }

    setParsing(true);
    setError(null);
    setResult(null);

    try {
      const res = await novelApi.parse({
        project_id: selectedProject,
        story_input: content,
      });
      // 兼容后端返回可能直接是 data 或包裹在 data 字段中
      const data: NovelParseResult = res?.data ?? res ?? EMPTY_RESULT;
      setResult(data);
      message.success('解析完成');
    } catch (e: any) {
      const msg = e?.message || '解析失败，请重试';
      setError(msg);
      message.error(msg);
    } finally {
      setParsing(false);
    }
  }, [selectedProject, content]);

  /* ---- 清空 ---- */

  const handleClear = () => {
    setContent('');
    setResult(null);
    setError(null);
  };

  /* ---- 人物表格列 ---- */

  const characterColumns = [
    {
      title: '姓名', dataIndex: 'name', key: 'name', width: 100,
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: '角色定位', dataIndex: 'role', key: 'role', width: 120,
      render: (v: string) => <Tag color="purple">{v || '未设定'}</Tag>,
    },
    {
      title: '年龄', dataIndex: 'age', key: 'age', width: 60,
      render: (v: string) => v || '-',
    },
    {
      title: '性别', dataIndex: 'gender', key: 'gender', width: 60,
      render: (v: string) => v || '-',
    },
    {
      title: '性格', dataIndex: 'personality', key: 'personality', width: 120,
      ellipsis: true,
    },
    {
      title: '外貌', dataIndex: 'appearance', key: 'appearance', width: 160,
      ellipsis: true,
    },
    {
      title: '背景', dataIndex: 'background', key: 'background',
      ellipsis: true,
    },
  ];

  /* ---- 章节表格列 ---- */

  const chapterColumns = [
    {
      title: '序号', dataIndex: 'order', key: 'order', width: 60,
      render: (_: any, __: any, i: number) => i + 1,
    },
    {
      title: '章节标题', dataIndex: 'title', key: 'title', width: 200,
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: '概要', dataIndex: 'summary', key: 'summary',
      ellipsis: true,
    },
  ];

  /* ---- 主题展示 ---- */

  const renderThemes = () => {
    if (!result?.themes || result.themes.length === 0) {
      return <Empty description="暂无主题信息" />;
    }
    return (
      <Row gutter={[16, 16]}>
        {result.themes.map((theme, idx) => (
          <Col span={8} key={idx}>
            <Card size="small" className="agent-card" style={{ height: '100%' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text strong style={{ color: '#7c3aed', fontSize: 15 }}>
                  {theme.name}
                </Text>
                {theme.description && (
                  <Text type="secondary" style={{ fontSize: 13 }}>
                    {theme.description}
                  </Text>
                )}
                {theme.keywords && theme.keywords.length > 0 && (
                  <Space wrap>
                    {theme.keywords.map((kw, ki) => (
                      <Tag key={ki} color="purple">{kw}</Tag>
                    ))}
                  </Space>
                )}
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    );
  };

  /* ---- 世界观设定 ---- */

  const renderWorldSetting = () => {
    const ws = result?.world_setting;
    if (!ws || Object.keys(ws).length === 0) {
      return <Empty description="暂无世界观设定" />;
    }

    const fields: Array<{ label: string; key: keyof ParsedWorldSetting }> = [
      { label: '世界名称', key: 'name' },
      { label: '时代背景', key: 'time_period' },
      { label: '地理环境', key: 'geography' },
      { label: '魔法体系', key: 'magic_system' },
      { label: '科技水平', key: 'technology_level' },
      { label: '文化风俗', key: 'culture' },
      { label: '整体描述', key: 'description' },
    ];

    const visibleFields = fields.filter((f) => ws[f.key]);

    if (visibleFields.length === 0) {
      return <Empty description="暂无世界观设定" />;
    }

    return (
      <Descriptions column={2} bordered size="small">
        {visibleFields.map((f) => (
          <Descriptions.Item label={f.label} key={f.key} span={f.key === 'description' ? 2 : 1}>
            {ws[f.key]}
          </Descriptions.Item>
        ))}
      </Descriptions>
    );
  };

  /* ---- Tab 项 ---- */

  const tabItems = [
    {
      key: 'characters',
      label: (
        <Space>
          <TeamOutlined />
          人物 ({result?.characters?.length ?? 0})
        </Space>
      ),
      children: (
        <Table
          dataSource={result?.characters ?? []}
          columns={characterColumns}
          rowKey={(_, idx) => String(idx)}
          size="small"
          pagination={false}
          locale={{ emptyText: <Empty description="未识别到人物" /> }}
        />
      ),
    },
    {
      key: 'chapters',
      label: (
        <Space>
          <FileTextOutlined />
          章节 ({result?.chapters?.length ?? 0})
        </Space>
      ),
      children: (
        <Table
          dataSource={result?.chapters ?? []}
          columns={chapterColumns}
          rowKey={(_, idx) => String(idx)}
          size="small"
          pagination={false}
          locale={{ emptyText: <Empty description="未识别到章节" /> }}
        />
      ),
    },
    {
      key: 'themes',
      label: (
        <Space>
          <ThunderboltOutlined />
          主题 ({result?.themes?.length ?? 0})
        </Space>
      ),
      children: renderThemes(),
    },
    {
      key: 'world',
      label: (
        <Space>
          <GlobalOutlined />
          世界观设定
        </Space>
      ),
      children: renderWorldSetting(),
    },
  ];

  /* ---- 渲染 ---- */

  return (
    <div>
      {/* 页面标题 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <BookOutlined /> 小说解析
          </Title>
          <Text type="secondary">粘贴小说内容，AI 自动解析人物、章节、主题和世界观</Text>
        </Col>
        <Col>
          <Space>
            <Select
              style={{ width: 220 }}
              placeholder="选择项目"
              allowClear
              value={selectedProject || undefined}
              onChange={(v) => setSelectedProject(v || '')}
              options={projects.map((p) => ({ label: p.name, value: p.id }))}
            />
            <Tooltip title="清空输入和结果">
              <Button icon={<ClearOutlined />} onClick={handleClear}>
                清空
              </Button>
            </Tooltip>
          </Space>
        </Col>
      </Row>

      {/* 输入区 */}
      <Card size="small" style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text strong style={{ marginBottom: 8, display: 'block' }}>
              小说原文
            </Text>
            <TextArea
              rows={12}
              placeholder="在此粘贴小说正文内容，支持长篇文本..."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              style={{ fontFamily: 'inherit' }}
            />
          </div>
          <Row justify="space-between" align="middle">
            <Col>
              <Text type="secondary" style={{ fontSize: 13 }}>
                已输入 {content.length} 字符
              </Text>
            </Col>
            <Col>
              <Space>
                <Button
                  type="primary"
                  icon={<ThunderboltOutlined />}
                  onClick={handleParse}
                  loading={parsing}
                  disabled={!selectedProject || !content.trim()}
                  style={{
                    background: 'linear-gradient(135deg, #7c3aed, #a855f7)',
                    borderColor: '#7c3aed',
                  }}
                >
                  {parsing ? '解析中...' : '开始解析'}
                </Button>
                <Button icon={<ReloadOutlined />} onClick={handleClear}>
                  重置
                </Button>
              </Space>
            </Col>
          </Row>
        </Space>
      </Card>

      {/* 错误提示 */}
      {error && (
        <Alert
          type="error"
          message="解析失败"
          description={error}
          closable
          showIcon
          style={{ marginBottom: 24 }}
          onClose={() => setError(null)}
        />
      )}

      {/* 解析中占位 */}
      {parsing && (
        <Card size="small">
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              minHeight: 200,
              flexDirection: 'column',
              gap: 16,
            }}
          >
            <Spin size="large" />
            <Text type="secondary">AI 正在解析小说内容，请稍候...</Text>
          </div>
        </Card>
      )}

      {/* 解析结果 */}
      {!parsing && result && (
        <Card size="small" className="agent-card">
          <Tabs items={tabItems} />
        </Card>
      )}

      {/* 空状态 */}
      {!parsing && !result && !error && (
        <Card size="small">
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Space direction="vertical" style={{ textAlign: 'center' }}>
                <Text type="secondary">选择项目并粘贴小说内容后，点击"开始解析"</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  AI 将自动提取人物、章节、主题和世界观设定
                </Text>
              </Space>
            }
          />
        </Card>
      )}
    </div>
  );
};

export default NovelParserPage;