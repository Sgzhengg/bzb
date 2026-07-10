import React, { useState, useEffect } from "react";
import {
  Card, Typography, Button, Space, message, Row, Col,
  Divider, Input, Select, Switch, Statistic, Spin,
} from "antd";
import {
  ApiOutlined, RobotOutlined, SaveOutlined, DatabaseOutlined,
} from "@ant-design/icons";
import { saveLLMConfig } from "../services/api";
import apiClient from "../services/api";

const { Title, Text, Paragraph } = Typography;

function Settings() {
  const [llmEnabled, setLLMEnabled] = useState(true);
  const [llmApiKey, setLLMApiKey] = useState("");
  const [llmModel, setLLMModel] = useState("deepseek-chat");
  const [llmBaseUrl, setLLMBaseUrl] = useState("https://api.deepseek.com/v1");
  const [sysStats, setSysStats] = useState(null);

  useEffect(() => {
    apiClient.get("/health").then(d => setSysStats(d)).catch(() => {});
  }, []);

  return (
    <div>
      <Title level={3}><RobotOutlined /> 设置</Title>

        <Card title={<><DatabaseOutlined /> 系统状态</>} style={{ maxWidth: 650, marginBottom: 16 }}>
          {sysStats ? (
            <Row gutter={24}>
              <Col span={8}>
                <Statistic title="服务状态" value={sysStats.status === "ok" ? "正常" : "异常"}
                  valueStyle={{ color: "#52c41a", fontSize: 20 }} />
              </Col>
              <Col span={8}>
                <Statistic title="AI 引擎" value={sysStats.llm?.model || "—"}
                  valueStyle={{ fontSize: 16 }} />
              </Col>
              <Col span={8}>
                <Statistic title="版本" value={sysStats.version || "—"}
                  valueStyle={{ fontSize: 16 }} />
              </Col>
            </Row>
          ) : (
            <Spin size="small" />
          )}
        </Card>

        <Card
          title={<><RobotOutlined /> AI 智能分析配置</>}
          style={{ maxWidth: 650, marginBottom: 16 }}
        >
          <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
            配置 LLM API 以启用智能竞品分析、趋势洞察和异常检测功能。
            支持 DeepSeek、OpenAI 等兼容接口。
          </Text>
          <Row gutter={[16, 12]}>
            <Col span={24}>
              <Space>
                <Switch checked={llmEnabled} onChange={setLLMEnabled} />
                <Text>启用 AI 分析</Text>
              </Space>
            </Col>
            <Col span={24}>
              <Text>API 地址</Text>
              <Input
                value={llmBaseUrl}
                onChange={e => setLLMBaseUrl(e.target.value)}
                placeholder="https://api.deepseek.com/v1"
                style={{ marginTop: 4 }}
              />
            </Col>
            <Col span={24}>
              <Text>API Key</Text>
              <Input.Password
                value={llmApiKey}
                onChange={e => setLLMApiKey(e.target.value)}
                placeholder="sk-..."
                style={{ marginTop: 4 }}
              />
            </Col>
            <Col span={12}>
              <Text>模型</Text>
              <Select
                value={llmModel}
                onChange={setLLMModel}
                style={{ width: "100%", marginTop: 4 }}
                options={[
                  { value: "deepseek-chat", label: "DeepSeek V3" },
                  { value: "deepseek-reasoner", label: "DeepSeek R1" },
                  { value: "gpt-4o-mini", label: "GPT-4o Mini" },
                  { value: "gpt-4o", label: "GPT-4o" },
                ]}
              />
            </Col>
          </Row>
          <Divider />
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={async () => {
              try {
                await saveLLMConfig({
                  llm_enabled: llmEnabled,
                  llm_api_key: llmApiKey,
                  llm_model: llmModel,
                  llm_base_url: llmBaseUrl,
                });
                message.success("AI 配置已保存");
              } catch {
                message.error("保存失败");
              }
            }}
          >
            保存 AI 配置
          </Button>
        </Card>

        <Card title="关于标中宝" style={{ maxWidth: 650 }}>
          <Paragraph>标中宝 V1.0.0 — 广东移动广告招标情报系统</Paragraph>
          <Paragraph type="secondary">
            技术栈：React 18 + Ant Design 5 + FastAPI + PostgreSQL
          </Paragraph>
          <Paragraph type="secondary">
            AI 引擎：DeepSeek / OpenAI 兼容接口
          </Paragraph>
        </Card>
    </div>
  );
}

export default Settings;
