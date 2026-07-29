import React from "react";
import { Card, Typography } from "antd";
import { SettingOutlined } from "@ant-design/icons";

const { Title, Paragraph, Text } = Typography;

function Settings() {
  return (
    <div>
      <Title level={3}><SettingOutlined /> 设置</Title>

      <Card title="关于标中宝" style={{ maxWidth: 650, marginBottom: 16 }}>
        <Paragraph>标中宝 V1.0.0 — 招标情报系统</Paragraph>
        <Paragraph type="secondary">
          技术栈：React 18 + Ant Design 5 + FastAPI + PostgreSQL
        </Paragraph>
        <Paragraph type="secondary">
          AI 引擎：DeepSeek / OpenAI 兼容接口
        </Paragraph>
      </Card>

      <Card title="使用帮助" style={{ maxWidth: 650 }}>
        <Paragraph>
          <Text strong>机会列表</Text> — 浏览和筛选招标公告，按推荐指数排序，支持关键词搜索和多维度过滤。
        </Paragraph>
        <Paragraph>
          <Text strong>中标结果</Text> — 查看历史中标记录，分析竞争对手中标情况。
        </Paragraph>
        <Paragraph>
          <Text strong>客情管理</Text> — 管理采购方关系，设置提醒和评级。
        </Paragraph>
        <Paragraph>
          <Text strong>数据看板</Text> — 可视化数据概览，地市对比分析。
        </Paragraph>
        <Paragraph type="secondary" style={{ marginTop: 16 }}>
          系统配置和管理请访问 <a href="/admin">管理后台</a>。
        </Paragraph>
      </Card>
    </div>
  );
}

export default Settings;
