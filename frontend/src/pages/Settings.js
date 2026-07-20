import React, { useState, useEffect } from "react";
import {
  Card, Typography, Button, Space, App, Row, Col,
  Divider, Input, Select, Switch, Statistic, Spin,
} from "antd";
import {
  ApiOutlined, RobotOutlined, SaveOutlined, DatabaseOutlined,
  CloudDownloadOutlined,
} from "@ant-design/icons";
import { saveLLMConfig } from "../services/api";
import apiClient from "../services/api";

const { Title, Text, Paragraph } = Typography;

function Settings() {
  const { message } = App.useApp();
  const [llmEnabled, setLLMEnabled] = useState(true);
  const [llmApiKey, setLLMApiKey] = useState("");
  const [llmModel, setLLMModel] = useState("deepseek-chat");
  const [llmBaseUrl, setLLMBaseUrl] = useState("https://api.deepseek.com/v1");
  const [sysStats, setSysStats] = useState(null);

  // V3: 采集偏好
  const [defaultSources, setDefaultSources] = useState(["b2b_10086"]);
  const [defaultProvinces, setDefaultProvinces] = useState(["广东"]);
  const [autoCollect, setAutoCollect] = useState(false);
  const [collectFreq, setCollectFreq] = useState("manual");

  useEffect(() => {
    apiClient.get("/health").then(d => setSysStats(d)).catch(() => {});
    // 加载偏好
    apiClient.get("/preferences").then(d => {
      if (d.default_data_sources?.length) setDefaultSources(d.default_data_sources);
      if (d.default_provinces?.length) setDefaultProvinces(d.default_provinces);
      if (d.auto_collect_enabled) setAutoCollect(d.auto_collect_enabled === "true");
      if (d.collect_frequency) setCollectFreq(d.collect_frequency);
    }).catch(() => {});
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

        <Card
          title={<><CloudDownloadOutlined /> 采集偏好</>}
          style={{ maxWidth: 650, marginBottom: 16 }}
        >
          <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
            设置默认采集源和省份，影响"采集数据"快捷按钮和定时采集行为。
          </Text>
          <Row gutter={[16, 12]}>
            <Col span={24}>
              <Text>默认采集源</Text>
              <Select mode="multiple" value={defaultSources} onChange={setDefaultSources}
                style={{ width: "100%", marginTop: 4 }}
                options={[
                  { value: "b2b_10086", label: "中国移动" },
                  { value: "telecom", label: "中国电信" },
                  { value: "unicom", label: "中国联通" },
                  { value: "gd_zbtb", label: "广东招标监管网" },
                  { value: "gd_ygp", label: "广东公共资源平台" },
                ]}
                placeholder="选择默认采集源"
              />
            </Col>
            <Col span={24}>
              <Text>默认采集省份</Text>
              <Select mode="multiple" value={defaultProvinces} onChange={setDefaultProvinces}
                style={{ width: "100%", marginTop: 4 }}
                options={["广东","广西","福建","海南","浙江","湖南","安徽","山东","江苏","四川","湖北","河南","北京","上海","重庆","天津"].map(p => ({ value: p, label: p }))}
                placeholder="选择默认省份"
              />
            </Col>
            <Col span={12}>
              <Space>
                <Switch checked={autoCollect} onChange={setAutoCollect} />
                <Text>启用自动采集</Text>
              </Space>
            </Col>
            <Col span={12}>
              <Select value={collectFreq} onChange={setCollectFreq}
                style={{ width: "100%" }}
                options={[
                  { value: "manual", label: "手动采集" },
                  { value: "daily", label: "每日 1 次" },
                  { value: "twice_daily", label: "每日 2 次" },
                ]}
              />
            </Col>
          </Row>
          <Divider />
          <Button type="primary" icon={<SaveOutlined />}
            onClick={async () => {
              try {
                await apiClient.put("/preferences", {
                  default_data_sources: defaultSources,
                  default_provinces: defaultProvinces,
                  auto_collect_enabled: autoCollect ? "true" : "false",
                  collect_frequency: collectFreq,
                });
                message.success("采集偏好已保存");
              } catch { message.error("保存失败"); }
            }}
          >
            保存采集偏好
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
