import React, { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Typography, Tag, Table, Space } from "antd";
import {
  FileTextOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  StarOutlined,
} from "@ant-design/icons";
import { getHealthStatus, getMockBiddingData } from "../services/api";

const { Title } = Typography;

const columns = [
  {
    title: "项目名称",
    dataIndex: "projectName",
    key: "projectName",
    ellipsis: true,
  },
  {
    title: "采购单位",
    dataIndex: "purchaser",
    key: "purchaser",
  },
  {
    title: "预算金额",
    dataIndex: "budget",
    key: "budget",
  },
  {
    title: "发布日期",
    dataIndex: "publishDate",
    key: "publishDate",
  },
  {
    title: "状态",
    dataIndex: "status",
    key: "status",
    render: (status) => {
      const colorMap = {
        招标中: "processing",
        已截止: "default",
        已中标: "success",
      };
      return <Tag color={colorMap[status] || "default"}>{status}</Tag>;
    },
  },
];

function Dashboard() {
  const [health, setHealth] = useState(null);
  const [biddingData, setBiddingData] = useState([]);

  useEffect(() => {
    getHealthStatus()
      .then((data) => setHealth(data))
      .catch(() => setHealth({ status: "disconnected" }));

    getMockBiddingData()
      .then((data) => setBiddingData(data))
      .catch(() => setBiddingData([]));
  }, []);

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        📋 数据看板
      </Title>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="招标总数"
              value={156}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: "#1677ff" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="招标中"
              value={32}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: "#fa8c16" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="已中标"
              value={98}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: "#52c41a" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="关注项目"
              value={12}
              prefix={<StarOutlined />}
              valueStyle={{ color: "#eb2f96" }}
            />
          </Card>
        </Col>
      </Row>

      {/* 服务状态 */}
      <Card style={{ marginBottom: 24 }}>
        <Space>
          <span>后端服务状态：</span>
          <Tag color={health?.status === "ok" ? "success" : "error"}>
            {health?.status === "ok" ? "运行正常 ✅" : "未连接 ❌"}
          </Tag>
          {health?.version && (
            <span style={{ color: "#888" }}>版本: {health.version}</span>
          )}
        </Space>
      </Card>

      {/* 招标数据表格 */}
      <Card title="📌 近期待分析招标项目">
        <Table
          columns={columns}
          dataSource={biddingData}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 800 }}
        />
      </Card>
    </div>
  );
}

export default Dashboard;
