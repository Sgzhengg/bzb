import React from "react";
import { Card, Typography } from "antd";
import { ToolOutlined } from "@ant-design/icons";

const { Title, Paragraph } = Typography;

function PurchaserProfile() {
  return (
    <div style={{ display: "flex", justifyContent: "center", paddingTop: 80 }}>
      <Card style={{ maxWidth: 500, textAlign: "center" }}>
        <ToolOutlined style={{ fontSize: 64, color: "#1677ff", marginBottom: 16 }} />
        <Title level={4}>采购方画像</Title>
        <Paragraph type="secondary">功能开发中，敬请期待...</Paragraph>
      </Card>
    </div>
  );
}

export default PurchaserProfile;
