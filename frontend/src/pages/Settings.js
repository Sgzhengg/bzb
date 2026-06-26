import React from "react";
import { Card, Checkbox, Typography, Button, Space, message, Row, Col } from "antd";
import { SaveOutlined } from "@ant-design/icons";
import { getPurchaserProfile } from "../services/api";

const { Title, Text } = Typography;

const CATEGORIES = [
  { value: "品牌策略类", label: "品牌策略", color: "magenta" },
  { value: "创意设计类", label: "创意设计", color: "purple" },
  { value: "媒介投放类", label: "媒介投放", color: "cyan" },
  { value: "活动执行类", label: "活动执行", color: "orange" },
  { value: "内容制作类", label: "内容制作", color: "geekblue" },
  { value: "新媒体运营类", label: "新媒体运营", color: "green" },
];

function Settings() {
  return (
    <div>
      <Title level={3}>⚙️ 设置</Title>

      <Card title="项目类型偏好" style={{ maxWidth: 600 }}>
        <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
          勾选您擅长的赛道。机会评分时会优先推荐匹配的项目。
        </Text>
        <Checkbox.Group style={{ width: "100%" }}>
          <Row gutter={[8, 8]}>
            {CATEGORIES.map(cat => (
              <Col span={12} key={cat.value}>
                <Checkbox value={cat.value}>{cat.label}</Checkbox>
              </Col>
            ))}
          </Row>
        </Checkbox.Group>
        <div style={{ marginTop: 24 }}>
          <Button type="primary" icon={<SaveOutlined />} onClick={() => message.success("偏好已保存")}>
            保存偏好
          </Button>
        </div>
      </Card>

      <Card title="关于标中宝" style={{ maxWidth: 600, marginTop: 16 }}>
        <Text>
          标中宝 V1.0.0 — 广东移动广告招标情报系统
        </Text>
        <br />
        <Text type="secondary">
          技术栈：React 18 + Ant Design 5 + FastAPI + PostgreSQL
        </Text>
      </Card>
    </div>
  );
}

export default Settings;
