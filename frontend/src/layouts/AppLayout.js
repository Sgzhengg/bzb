import React, { useState, useEffect } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { Layout, Menu, Typography, Badge, Space, Statistic, Card, Row, Col } from "antd";
import {
  ThunderboltOutlined, BankOutlined, UserOutlined,
  EnvironmentOutlined, SettingOutlined, BellOutlined,
  FileTextOutlined, RiseOutlined,
} from "@ant-design/icons";
import { getRelationReminders } from "../services/api";

const { Header, Content, Sider } = Layout;
const { Title } = Typography;

function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [reminderCount, setReminderCount] = useState(0);

  const menuItems = [
    { key: "/opportunities", icon: <ThunderboltOutlined />, label: "机会列表" },
    { key: "/purchaser-profile", icon: <BankOutlined />, label: "采购方画像" },
    { key: "/client-relations", icon: <UserOutlined />, label: "客情管理" },
    { key: "/region-compare", icon: <EnvironmentOutlined />, label: "地市对比" },
    { key: "/settings", icon: <SettingOutlined />, label: "设置" },
  ];

  // 定时获取提醒数量
  useEffect(() => {
    const fetchReminders = () => {
      getRelationReminders()
        .then(data => setReminderCount(Array.isArray(data) ? data.length : 0))
        .catch(() => {});
    };
    fetchReminders();
    const timer = setInterval(fetchReminders, 60000);
    return () => clearInterval(timer);
  }, []);

  const selectedKey = "/" + location.pathname.split("/")[1];

  return (
    <Layout style={{ minHeight: "100vh" }}>
      {/* 顶部导航栏 */}
      <Header style={{
        background: "#001529", padding: "0 24px", display: "flex",
        alignItems: "center", justifyContent: "space-between",
        position: "sticky", top: 0, zIndex: 100,
      }}>
        <Space size={40}>
          <Title level={4} style={{ color: "#fff", margin: 0, whiteSpace: "nowrap" }}>
            📊 标中宝 V1
          </Title>
          <Menu
            theme="dark" mode="horizontal"
            selectedKeys={[selectedKey]}
            onClick={({ key }) => navigate(key)}
            items={menuItems}
            style={{ flex: 1, minWidth: 500, borderBottom: "none" }}
          />
        </Space>
        <Space>
          <Badge count={reminderCount} size="small" offset={[-2, 2]}>
            <BellOutlined style={{ color: "#fff", fontSize: 18, cursor: "pointer" }}
              onClick={() => navigate("/client-relations")} />
          </Badge>
        </Space>
      </Header>

      <Layout>
        {/* 侧边栏统计 */}
        <Sider
          collapsible collapsed={collapsed} onCollapse={setCollapsed}
          width={220} theme="light"
          style={{ borderRight: "1px solid #f0f0f0", paddingTop: 16 }}
        >
          {!collapsed && <StatsPanel reminderCount={reminderCount} />}
        </Sider>

        {/* 内容区 */}
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

function StatsPanel({ reminderCount }) {
  const [stats, setStats] = useState({ newToday: 12, highOpp: 5, needFollow: reminderCount });

  useEffect(() => {
    setStats(s => ({ ...s, needFollow: reminderCount }));
  }, [reminderCount]);

  return (
    <div style={{ padding: "0 16px" }}>
      <Title level={5} style={{ marginBottom: 16 }}>📊 今日概览</Title>
      <Row gutter={[0, 12]}>
        <Col span={24}>
          <Card size="small">
            <Statistic title={<><FileTextOutlined /> 今日新增</>}
              value={stats.newToday} suffix="条" valueStyle={{ color: "#1677ff", fontSize: 20 }} />
          </Card>
        </Col>
        <Col span={24}>
          <Card size="small">
            <Statistic title={<><RiseOutlined /> 高机会</>}
              value={stats.highOpp} suffix="条" valueStyle={{ color: "#52c41a", fontSize: 20 }} />
          </Card>
        </Col>
        <Col span={24}>
          <Card size="small">
            <Statistic title={<><BellOutlined /> 需跟进</>}
              value={stats.needFollow} suffix="人" valueStyle={{ color: "#fa8c16", fontSize: 20 }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default AppLayout;
