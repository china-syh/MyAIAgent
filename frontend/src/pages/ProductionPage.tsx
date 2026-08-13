import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Form, Input, Progress, Select, Space, Tag, Typography, message } from 'antd';
import { productionApi } from '../api/client';

const labels: Record<string, string> = { planning: '故事规划', writing: '剧本生成', storyboarding: '分镜生成', prompting: '提示词优化', quality: '质量检查' };

const ProductionPage: React.FC = () => {
  const [form] = Form.useForm();
  const [run, setRun] = useState<any>();
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!run?.id || ['completed', 'failed'].includes(run.status)) return;
    const timer = window.setInterval(async () => setRun(await productionApi.get(run.id)), 2500);
    return () => window.clearInterval(timer);
  }, [run?.id, run?.status]);
  const start = async (values: any) => {
    setLoading(true);
    try { setRun(await productionApi.start(values.project_id, { story_input: values.story_input, genre: values.genre })); message.success('生产线已启动'); }
    catch (error: any) { message.error(error.message); }
    finally { setLoading(false); }
  };
  const refresh = async (action: Promise<any>) => setRun(await action);
  const completed = run?.stages?.filter((stage: any) => stage.status === 'completed').length || 0;
  const total = run?.stages?.length || 5;
  return <Space direction="vertical" size={20} style={{ width: '100%' }}>
    <div><Typography.Title level={2}>项目生产线</Typography.Title><Typography.Paragraph type="secondary">从故事输入开始，依次生成规划、剧本、分镜和提示词。</Typography.Paragraph></div>
    <Card title="启动生产"><Form form={form} layout="vertical" onFinish={start} initialValues={{ genre: 'fantasy' }}>
      <Form.Item name="project_id" label="项目 ID" rules={[{ required: true, message: '请输入项目 ID' }]}><Input placeholder="从项目管理页复制项目 ID" /></Form.Item>
      <Form.Item name="genre" label="类型"><Select options={[{ value: 'fantasy', label: '奇幻' }, { value: 'romance', label: '言情' }, { value: 'scifi', label: '科幻' }, { value: 'action', label: '动作' }]} /></Form.Item>
      <Form.Item name="story_input" label="故事输入"><Input.TextArea rows={6} placeholder="留空则使用项目中已保存的故事内容" /></Form.Item>
      <Button type="primary" htmlType="submit" loading={loading}>启动生产线</Button>
    </Form></Card>
    {run && <Card title="运行状态" extra={<Tag color={run.status === 'completed' ? 'success' : run.status === 'failed' ? 'error' : 'processing'}>{run.status}</Tag>}>
      <Progress percent={Math.round((completed / total) * 100)} status={run.status === 'failed' ? 'exception' : undefined} />
      {run.error && <Alert type="error" showIcon message={run.error} style={{ marginBottom: 16 }} />}
      <Space direction="vertical" style={{ width: '100%' }}>{run.stages.map((stage: any) => <Card size="small" key={stage.id} title={`${stage.order + 1}. ${labels[stage.name] || stage.name}`} extra={<Tag>{stage.status}</Tag>}>
        {stage.error && <Alert type="error" message={stage.error} />}{stage.status === 'failed' && <Button size="small" onClick={() => refresh(productionApi.retryStage(run.id, stage.name))}>重试阶段</Button>}
      </Card>)}</Space>
      <Space style={{ marginTop: 16 }}>{run.status === 'running' && <Button onClick={() => refresh(productionApi.pause(run.id))}>暂停</Button>}{(run.status === 'paused' || run.status === 'failed') && <Button type="primary" onClick={() => refresh(productionApi.resume(run.id))}>继续运行</Button>}</Space>
    </Card>}
  </Space>;
};
export default ProductionPage;
