import React, { useState } from "react";
import { Layout, Menu, Typography } from "antd";
import {
  DashboardOutlined,
  SearchOutlined,
  StarOutlined,
  SettingOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
  BankOutlined,
  UserOutlined,
  EnvironmentOutlined,
} from "@ant-design/icons";
import Dashboard from "../pages/Dashboard";
import OpportunityList from "../pages/OpportunityList";
import PurchaserProfile from "../pages/PurchaserProfile";
import RelationManagement from "../pages/RelationManagement";
import CityCompare from "../pages/CityCompare";

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

const menuItems = [
  {
    key: "dashboard",
    icon: <DashboardOutlined />,
    label: "数据看板",
  },
  {
    key: "opportunity",
    icon: <ThunderboltOutlined />,
    label: "机会列表",
  },
  {
    key: "profile",
    icon: <BankOutlined />,
    label: "采购方画像",
  },
  {
    key: "relations",
    icon: <UserOutlined />,
    label: "客情管理",
  },
  {
    key: "city-compare",
    icon: <EnvironmentOutlined />,
    label: "地市对比",
  },
  {
    key: "bidding-list",
    icon: <FileTextOutlined />,
    label: "招标列表",
  },
  {
    key: "analysis",
    icon: <SearchOutlined />,
    label: "情报分析",
  },
  {
    key: "favorites",
    icon: <StarOutlined />,
    label: "我的收藏",
  },
  {
    key: "settings",
    icon: <SettingOutlined />,
    label: "系统设置",
  },
];

function MainLayout() {
  const [currentPage, setCurrentPage] = useState("dashboard");

  const renderPage = () => {
    switch (currentPage) {
      case "opportunity":
        return <OpportunityList />;
      case "profile":
        return <PurchaserProfile />;
      case "relations":
        return <RelationManagement />;
      case "city-compare":
        return <CityCompare onNavigate={(page, id) => { if (page === "profile") { setCurrentPage("profile"); /* pass id via state */ } }} />;
      case "dashboard":
      default:
        return <Dashboard />;
    }
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider collapsible breakpoint="lg" theme="dark">
        <div
          style={{
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Title
            level={4}
            style={{ color: "#fff", margin: 0, whiteSpace: "nowrap" }}
          >
            📊 标中宝 V1
          </Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[currentPage]}
          onClick={({ key }) => setCurrentPage(key)}
          items={menuItems}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: "#fff",
            padding: "0 24px",
            display: "flex",
            alignItems: "center",
            boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
          }}
        >
          <Title level={4} style={{ margin: 0 }}>
            广东移动招标情报系统
          </Title>
        </Header>
        <Content
          style={{
            margin: 24,
            padding: 24,
            background: "#fff",
            borderRadius: 8,
            minHeight: 280,
          }}
        >
          {renderPage()}
        </Content>
      </Layout>
    </Layout>
  );
}

export default MainLayout;
