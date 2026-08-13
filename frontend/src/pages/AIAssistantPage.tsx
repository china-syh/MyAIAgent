import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Card,
  Button,
  Input,
  Select,
  Tag,
  Typography,
  Space,
  Spin,
  Empty,
  Avatar,
  Tooltip,
  Checkbox,
  message as antMessage,
} from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  BulbOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { aiAssistantApi, projectApi } from '../api/client';
import type { AIChatMessage, Project } from '../types';

const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;

// ─── 子组件：建议消息 ───────────────────────────────────────────
const SuggestionMessage: React.FC<{ content: string; metadata?: Record<string, unknown> }> = ({
  content,
  metadata,
}) => {
  const suggestions = metadata?.suggestions as string[] | undefined;

  return (
    <div>
      <Paragraph style={{ marginBottom: 8, whiteSpace: 'pre-wrap' }}>{content}</Paragraph>
      {suggestions && suggestions.length > 0 && (
        <Space wrap size={[4, 4]}>
          {suggestions.map((s, i) => (
            <Tag
              key={i}
              icon={<BulbOutlined />}
              color="purple"
              style={{ borderRadius: 12, padding: '2px 12px', cursor: 'pointer' }}
            >
              {s}
            </Tag>
          ))}
        </Space>
      )}
    </div>
  );
};

// ─── 子组件：审核消息 ───────────────────────────────────────────
const AuditMessage: React.FC<{ content: string; metadata?: Record<string, unknown> }> = ({
  content,
  metadata,
}) => {
  const checklist = (metadata?.checklist as { label: string; passed: boolean }[]) || [];

  return (
    <div>
      <Paragraph style={{ marginBottom: 8, whiteSpace: 'pre-wrap' }}>{content}</Paragraph>
      {checklist.length > 0 && (
        <div style={{ background: '#f9f0ff', borderRadius: 8, padding: '8px 12px', marginTop: 4 }}>
          {checklist.map((item, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <Checkbox checked={item.passed} disabled />
              <Text
                style={{
                  color: item.passed ? '#52c41a' : '#faad14',
                  fontSize: 13,
                }}
              >
                {item.label}
              </Text>
              {item.passed ? (
                <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 14 }} />
              ) : (
                <LoadingOutlined style={{ color: '#faad14', fontSize: 14 }} />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ─── 子组件：操作消息 ───────────────────────────────────────────
const ActionMessage: React.FC<{ content: string; metadata?: Record<string, unknown> }> = ({
  content,
  metadata,
}) => {
  const actions = (metadata?.actions as { label: string; key: string; type?: string }[]) || [];

  return (
    <div>
      <Paragraph style={{ marginBottom: 8, whiteSpace: 'pre-wrap' }}>{content}</Paragraph>
      {actions.length > 0 && (
        <Space wrap size={[8, 8]} style={{ marginTop: 4 }}>
          {actions.map((action, i) => (
            <Button
              key={i}
              icon={<ThunderboltOutlined />}
              size="small"
              type={action.type === 'primary' ? 'primary' : 'default'}
              ghost={action.type === 'primary'}
              style={{ borderRadius: 16 }}
            >
              {action.label}
            </Button>
          ))}
        </Space>
      )}
    </div>
  );
};

// ─── 消息气泡组件 ──────────────────────────────────────────────
const ChatBubble: React.FC<{ message: AIChatMessage }> = React.memo(({ message }) => {
  const isUser = message.role === 'user';

  const renderContent = () => {
    switch (message.message_type) {
      case 'suggestion':
        return <SuggestionMessage content={message.content} metadata={message.metadata} />;
      case 'audit':
        return <AuditMessage content={message.content} metadata={message.metadata} />;
      case 'action':
        return <ActionMessage content={message.content} metadata={message.metadata} />;
      default:
        return <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{message.content}</Paragraph>;
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: isUser ? 'row-reverse' : 'row',
        alignItems: 'flex-start',
        gap: 10,
        marginBottom: 16,
        padding: '0 4px',
      }}
    >
      {/* 头像 */}
      {isUser ? (
        <Avatar
          size={36}
          icon={<UserOutlined />}
          style={{ backgroundColor: '#1677ff', flexShrink: 0 }}
        />
      ) : (
        <Avatar
          size={36}
          icon={<RobotOutlined />}
          style={{ backgroundColor: '#722ed1', flexShrink: 0 }}
        />
      )}

      {/* 气泡 */}
      <div
        style={{
          maxWidth: '70%',
          minWidth: 60,
          padding: '10px 14px',
          borderRadius: 16,
          background: isUser ? '#1677ff' : '#f5f5f5',
          color: isUser ? '#fff' : '#333',
          borderTopLeftRadius: isUser ? 16 : 4,
          borderTopRightRadius: isUser ? 4 : 16,
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          position: 'relative',
        }}
      >
        {renderContent()}
        <Tooltip title={new Date(message.created_at).toLocaleString()}>
          <Text
            style={{
              display: 'block',
              fontSize: 11,
              color: isUser ? 'rgba(255,255,255,0.6)' : '#999',
              marginTop: 4,
              textAlign: isUser ? 'right' : 'left',
            }}
          >
            {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </Text>
        </Tooltip>
      </div>
    </div>
  );
});

ChatBubble.displayName = 'ChatBubble';

// ─── 主页面 ────────────────────────────────────────────────────
const AIAssistantPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | undefined>(undefined);
  const [messages, setMessages] = useState<AIChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);

  // ── 加载项目列表 ──
  useEffect(() => {
    setProjectsLoading(true);
    projectApi
      .list()
      .then((res) => {
        const list = Array.isArray(res) ? res : res?.data ?? res?.projects ?? [];
        setProjects(list);
      })
      .catch(() => {
        antMessage.error('加载项目列表失败');
      })
      .finally(() => setProjectsLoading(false));
  }, []);

  // ── 加载聊天记录 ──
  const loadChat = useCallback(async (projectId: string) => {
    setLoading(true);
    try {
      const res = await aiAssistantApi.getChat(projectId);
      const list = Array.isArray(res) ? res : res?.data ?? res?.messages ?? [];
      setMessages(list);
    } catch {
      antMessage.error('加载聊天记录失败');
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── 切换项目 ──
  const handleProjectChange = (value: string | undefined) => {
    setSelectedProjectId(value);
    setMessages([]);
    if (value) {
      loadChat(value);
    }
  };

  // ── 自动滚动到底部 ──
  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 50);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // ── 发送消息 ──
  const handleSend = useCallback(async () => {
    const text = inputValue.trim();
    if (!text || sending) return;

    // 乐观更新：添加用户消息
    const tempUserMessage: AIChatMessage = {
      id: `temp-${Date.now()}`,
      project_id: selectedProjectId ?? null,
      user_id: null,
      role: 'user',
      content: text,
      message_type: 'text',
      metadata: {},
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMessage]);
    setInputValue('');
    setSending(true);

    try {
      const res = await aiAssistantApi.sendMessage({
        project_id: selectedProjectId,
        content: text,
        message_type: 'text',
      });
      const reply = Array.isArray(res) ? res : res?.data ?? res?.message ?? res;
      if (Array.isArray(reply)) {
        setMessages((prev) => [...prev, ...reply]);
      } else if (reply && typeof reply === 'object') {
        // 处理 {user: {...}, assistant: {...}} 格式
        if (reply.user && reply.assistant) {
          setMessages((prev) => [...prev, reply.user as AIChatMessage, reply.assistant as AIChatMessage]);
        } else {
          setMessages((prev) => [...prev, reply as AIChatMessage]);
        }
      }
    } catch {
      antMessage.error('发送消息失败，请重试');
      // 移除临时消息
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMessage.id));
    } finally {
      setSending(false);
    }
  }, [inputValue, sending, selectedProjectId]);

  // ── 键盘事件：Enter 发送，Shift+Enter 换行 ──
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ── 渲染消息列表 ──
  const renderMessages = () => {
    if (loading) {
      return (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin indicator={<LoadingOutlined style={{ fontSize: 32 }} spin />} />
          <div style={{ marginTop: 12, color: '#999' }}>加载对话中...</div>
        </div>
      );
    }

    if (!selectedProjectId) {
      return (
        <Empty
          description="请先选择一个项目开始对话"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          style={{ padding: 60 }}
        />
      );
    }

    if (messages.length === 0) {
      return (
        <Empty
          description="暂无消息，开始和 AI 导演对话吧"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          style={{ padding: 60 }}
        />
      );
    }

    return messages.map((msg) => <ChatBubble key={msg.id} message={msg} />);
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: 16, background: '#f5f5f5' }}>
      {/* 头部：标题 + 项目选择器 */}
      <Card
        style={{
          marginBottom: 12,
          borderRadius: 12,
          boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
          flexShrink: 0,
        }}
        bodyStyle={{ padding: '12px 20px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <Space size={12}>
            <Avatar
              size={40}
              icon={<RobotOutlined />}
              style={{ backgroundColor: '#722ed1' }}
            />
            <div>
              <Title level={5} style={{ margin: 0 }}>AI 导演助手 - 夏导</Title>
              <Text type="secondary" style={{ fontSize: 12 }}>智能漫画创作助手，随时为您提供创意建议</Text>
            </div>
          </Space>

          <Select
            placeholder="选择项目"
            loading={projectsLoading}
            value={selectedProjectId}
            onChange={handleProjectChange}
            allowClear
            showSearch
            optionFilterProp="label"
            style={{ width: 260 }}
            options={projects.map((p) => ({
              value: p.id,
              label: p.name,
            }))}
            notFoundContent={projectsLoading ? <Spin size="small" /> : '暂无项目'}
          />
        </div>
      </Card>

      {/* 聊天区域 */}
      <Card
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          borderRadius: 12,
          boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
          overflow: 'hidden',
        }}
        bodyStyle={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          padding: 0,
          overflow: 'hidden',
        }}
      >
        {/* 消息列表 */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px 20px',
            background: '#fafafa',
          }}
        >
          {renderMessages()}
          {/* 发送中的加载指示器 */}
          {sending && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <Avatar
                size={36}
                icon={<RobotOutlined />}
                style={{ backgroundColor: '#722ed1', flexShrink: 0 }}
              />
              <div
                style={{
                  padding: '10px 14px',
                  borderRadius: 16,
                  borderTopLeftRadius: 4,
                  background: '#f5f5f5',
                  color: '#999',
                }}
              >
                <Space size={4}>
                  <LoadingOutlined />
                  <Text type="secondary">AI 正在思考...</Text>
                </Space>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <div
          style={{
            borderTop: '1px solid #f0f0f0',
            padding: '12px 20px 16px',
            background: '#fff',
          }}
        >
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
            <TextArea
              ref={textAreaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入您的问题，Enter 发送，Shift+Enter 换行..."
              autoSize={{ minRows: 1, maxRows: 4 }}
              disabled={sending}
              style={{ borderRadius: 10, resize: 'none' }}
            />
            <Tooltip title="发送 (Enter)">
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSend}
                loading={sending}
                disabled={!inputValue.trim() || !selectedProjectId}
                style={{
                  height: 40,
                  width: 44,
                  borderRadius: 10,
                  flexShrink: 0,
                }}
              />
            </Tooltip>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {selectedProjectId ? '已选择项目' : '请先选择一个项目'}
            </Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Enter 发送 · Shift+Enter 换行
            </Text>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default AIAssistantPage;