import React, { useState, useEffect, useCallback } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { Layout, Menu, Typography, Badge, Space, Statistic, Card } from "antd";
import {
  ThunderboltOutlined, TrophyOutlined, UserOutlined, SettingOutlined, BellOutlined, FileTextOutlined,
} from "@ant-design/icons";
import { getRelationReminders } from "../services/api";
import apiClient from "../services/api";

const { Header, Content, Sider } = Layout;
const { Title } = Typography;

const LS_KEY = "bzb_last_seen";

function getLastSeen() {
  try { return JSON.parse(localStorage.getItem(LS_KEY) || "{}"); }
  catch { return {}; }
}
function saveLastSeen(data) {
  localStorage.setItem(LS_KEY, JSON.stringify(data));
}

function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [reminderCount, setReminderCount] = useState(0);
  const [newAnnBadge, setNewAnnBadge] = useState(0);
  const [newAwardBadge, setNewAwardBadge] = useState(0);

  // 检查新数据（采集完成时通过 window._bzbCheckNew 调用）
  const checkNew = useCallback(async () => {
    try {
      const seen = getLastSeen();
      const [annRes, awardRes] = await Promise.all([
        apiClient.get("/announcements", { params: { page_size: 1 } }),
        apiClient.get("/awards", { params: { page_size: 1 } }),
      ]);
      const annTotal = annRes?.total || 0;
      const awardTotal = awardRes?.total || 0;
      const annNew = Math.max(0, annTotal - (seen.annTotal || 0));
      const awardNew = Math.max(0, awardTotal - (seen.awardTotal || 0));
      if (annNew > 0) setNewAnnBadge(prev => Math.max(prev, annNew));
      if (awardNew > 0) setNewAwardBadge(prev => Math.max(prev, awardNew));
    } catch {}
  }, []);

  useEffect(() => { checkNew(); }, [checkNew]);
  useEffect(() => {
    window._bzbCheckNew = checkNew;
    return () => { delete window._bzbCheckNew; };
  }, [checkNew]);

  // 导航到页面 → 清除对应角标 + 更新 lastSeen
  const go = async (key) => {
    const seen = getLastSeen();
    if (key === "/opportunities") {
      setNewAnnBadge(0);
      try {
        const res = await apiClient.get("/announcements", { params: { page_size: 1 } });
        saveLastSeen({ ...seen, annTotal: res?.total || seen.annTotal || 0 });
      } catch {}
    } else if (key === "/winning-results") {
      setNewAwardBadge(0);
      try {
        const res = await apiClient.get("/awards", { params: { page_size: 1 } });
        saveLastSeen({ ...seen, awardTotal: res?.total || seen.awardTotal || 0 });
      } catch {}
    }
    navigate(key);
  };

  const menuItems = [
    { key: "/opportunities", icon: <ThunderboltOutlined />, label: (
      <span>机会列表 {newAnnBadge > 0 && <Badge count={newAnnBadge} size="small" style={{ marginLeft: 6 }} />}</span>
    )},
    { key: "/winning-results", icon: <TrophyOutlined />, label: (
      <span>中标结果 {newAwardBadge > 0 && <Badge count={newAwardBadge} size="small" style={{ marginLeft: 6 }} />}</span>
    )},
    { key: "/client-relations", icon: <UserOutlined />, label: "客情管理" },
    { key: "/settings", icon: <SettingOutlined />, label: "设置" },
  ];

  // 定时获取提醒
  useEffect(() => {
    const f = () => getRelationReminders().then(d => setReminderCount(Array.isArray(d) ? d.length : 0)).catch(() => {});
    f();
    const t = setInterval(f, 60000);
    return () => clearInterval(t);
  }, []);

  const selectedKey = location.pathname === "/" ? "/opportunities" : "/" + location.pathname.split("/")[1];

  return (
    <Layout style={{ minHeight: "100vh" }}>
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
            onClick={({ key }) => go(key)}
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
        <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}
          width={220} theme="light"
          style={{ borderRight: "1px solid #f0f0f0", paddingTop: 16 }}>
          {!collapsed && <StatsPanel />}
        </Sider>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

function StatsPanel() {
  const [newToday, setNewToday] = useState(0);
  useEffect(() => {
    import("../services/api").then(({ default: api }) => {
      api.get("/overview/today").then(d => setNewToday(d.new_today || 0)).catch(() => {});
    });
  }, []);
  return (
    <div style={{ padding: "0 16px" }}>
      <Title level={5} style={{ marginBottom: 16 }}>📊 今日概览</Title>
      <Card size="small">
        <Statistic title={<><FileTextOutlined /> 今日新增</>}
          value={newToday} suffix="条" valueStyle={{ color: "#1677ff", fontSize: 20 }} />
      </Card>
    </div>
  );
}

export default AppLayout;
