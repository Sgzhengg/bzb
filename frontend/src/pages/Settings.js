import React, { useState, useEffect } from "react";
import {
  Card, Checkbox, Typography, Button, Space, message, Row, Col,
  InputNumber, Divider, Spin, Tag
} from "antd";
import {
  SaveOutlined, ReloadOutlined,
  FilterOutlined
} from "@ant-design/icons";
import { getPreferences, updatePreferences, resetPreferences } from "../services/api";

const { Title, Text, Paragraph } = Typography;

const CATEGORIES = [
  { value: "品牌策略类", label: "品牌策略", color: "magenta" },
  { value: "创意设计类", label: "创意设计", color: "purple" },
  { value: "媒介投放类", label: "媒介投放", color: "cyan" },
  { value: "活动会展类", label: "活动会展", color: "orange" },
  { value: "渠道营销类", label: "渠道营销", color: "volcano" },
  { value: "内容制作类", label: "内容制作", color: "geekblue" },
  { value: "政企传播类", label: "政企传播", color: "red" },
  { value: "新媒体运营类", label: "新媒体运营", color: "green" },
];

function Settings() {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [preferredCats, setPreferredCats] = useState([]);
  const [minBudget, setMinBudget] = useState(0);
  const [minScore, setMinScore] = useState(0);

  useEffect(() => { loadPreferences(); }, []);

  const loadPreferences = async () => {
    setLoading(true);
    try {
      const data = await getPreferences();
      setPreferredCats(data.preferred_categories || []);
      setMinBudget(data.min_budget || 0);
      setMinScore(data.min_score || 0);
    } catch (err) {
      console.error("加载偏好失败:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updatePreferences({
        preferred_categories: preferredCats,
        min_budget: minBudget,
        min_score: minScore,
      });
      message.success("偏好已保存，首页将按新偏好筛选");
    } catch (err) {
      message.error("保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    try {
      await resetPreferences();
      setPreferredCats([]);
      setMinBudget(0);
      setMinScore(0);
      message.success("偏好已重置");
    } catch (err) {
      message.error("重置失败");
    }
  };

  return (
    <Spin spinning={loading}>
      <div>
        <Title level={3}><FilterOutlined /> 设置</Title>

        <Card title="偏好赛道" style={{ maxWidth: 650, marginBottom: 16 }}>
          <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
            勾选你擅长的赛道。机会列表会将匹配项目优先展示。
          </Text>
          <Checkbox.Group
            value={preferredCats}
            onChange={setPreferredCats}
            style={{ width: "100%" }}
          >
            <Row gutter={[8, 8]}>
              {CATEGORIES.map(cat => (
                <Col span={12} key={cat.value}>
                  <Checkbox value={cat.value}>
                    <Tag color={cat.color}>{cat.label}</Tag>
                  </Checkbox>
                </Col>
              ))}
            </Row>
          </Checkbox.Group>
        </Card>

        <Card title="过滤条件" style={{ maxWidth: 650, marginBottom: 16 }}>
          <Row gutter={24}>
            <Col span={12}>
              <Text>最低预算（万元）</Text>
              <InputNumber
                value={minBudget}
                onChange={setMinBudget}
                min={0} max={10000} step={10}
                placeholder="0 = 不限"
                style={{ width: "100%", marginTop: 4 }}
                addonAfter="万"
              />
            </Col>
            <Col span={12}>
              <Text>最低机会评分</Text>
              <InputNumber
                value={minScore}
                onChange={setMinScore}
                min={0} max={100} step={5}
                placeholder="0 = 不限"
                style={{ width: "100%", marginTop: 4 }}
                addonAfter="分"
              />
            </Col>
          </Row>
        </Card>

        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>
            保存偏好
          </Button>
          <Button icon={<ReloadOutlined />} onClick={handleReset}>
            重置为默认
          </Button>
        </Space>

        <Divider />

        <Card title="关于标中宝" style={{ maxWidth: 650 }}>
          <Paragraph>标中宝 V1.0.0 — 广东移动广告招标情报系统</Paragraph>
          <Paragraph type="secondary">
            技术栈：React 18 + Ant Design 5 + FastAPI + PostgreSQL
          </Paragraph>
        </Card>
      </div>
    </Spin>
  );
}

export default Settings;
