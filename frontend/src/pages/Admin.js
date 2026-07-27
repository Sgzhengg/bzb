import React, { useState, useEffect } from "react";
import {
  Card, Typography, Button, App, Form, Input, Row, Col, Statistic,
  Table, Tag, Space, Spin,
} from "antd";
import {
  UserOutlined, SafetyCertificateOutlined, LockOutlined, LoginOutlined,
  ApiOutlined, DatabaseOutlined, LogoutOutlined, RobotOutlined,
} from "@ant-design/icons";
import apiClient from "../services/api";

const { Title, Text } = Typography;

function Admin() {
  const { message } = App.useApp();
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginForm] = Form.useForm();
  const [currentUser, setCurrentUser] = useState(null);
  const [sysStats, setSysStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 管理后台不自动登录，清除旧 token，始终要求重新认证
    localStorage.removeItem("bzb_token");
    apiClient.get("/health").then(d => setSysStats(d)).catch(() => {});
    setLoading(false);
  }, []);

  const handleLogin = async (values) => {
    setLoginLoading(true);
    try {
      const result = await apiClient.post("/auth/login", values);
      localStorage.setItem("bzb_token", result.access_token);
      message.success(`欢迎, ${result.display_name || result.username}`);
      setCurrentUser({
        id: result.id,
        username: result.username,
        display_name: result.display_name,
        is_admin: result.is_admin,
      });
    } catch (e) {
      message.error("登录失败: " + (e.response?.data?.detail || e.message));
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("bzb_token");
    setCurrentUser(null);
    loginForm.resetFields();
    message.info("已退出登录");
  };

  if (loading) {
    return <div style={{ textAlign: "center", padding: 100 }}><Spin size="large" /></div>;
  }

  // ── 未登录 → 登录表单 ──
  if (!currentUser) {
    return (
      <div style={{ maxWidth: 460, margin: "0 auto", paddingTop: 40 }}>
        <Card styles={{ body: { padding: "32px 32px 24px" } }}>
          <div style={{ textAlign: "center", marginBottom: 24 }}>
            <SafetyCertificateOutlined style={{ fontSize: 40, color: "#1677ff" }} />
            <Title level={4} style={{ marginTop: 8, marginBottom: 2 }}>管理员登录</Title>
            <Text type="secondary">请使用管理员账户登录以访问管理后台</Text>
          </div>
          <Form form={loginForm} onFinish={handleLogin} size="large" initialValues={{ username: "admin" }}>
            <Form.Item name="username" rules={[{ required: true, message: "请输入用户名" }]}>
              <Input prefix={<UserOutlined />} placeholder="用户名" autoFocus />
            </Form.Item>
            <Form.Item name="password" rules={[{ required: true, message: "请输入密码" }]}>
              <Input.Password prefix={<LockOutlined />} placeholder="密码" />
            </Form.Item>
            <Form.Item style={{ marginBottom: 0 }}>
              <Button type="primary" htmlType="submit" loading={loginLoading} icon={<LoginOutlined />} block>
                登 录
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </div>
    );
  }

  // ── 已登录 → 管理后台仪表盘 ──
  return (
    <div>
      <Title level={3}><SafetyCertificateOutlined /> 管理后台</Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="服务状态" value={sysStats?.status === "ok" ? "正常" : "异常"}
              valueStyle={{ color: sysStats?.status === "ok" ? "#52c41a" : "#ff4d4f" }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="数据库" value={sysStats?.database?.includes("sqlite") ? "SQLite" : "PostgreSQL"} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="AI 引擎" value={sysStats?.llm?.available ? "可用" : "未启用"}
              valueStyle={{ color: sysStats?.llm?.available ? "#52c41a" : "#999" }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="爬虫状态" value={sysStats?.crawler?.enabled ? "启用" : "禁用"}
              valueStyle={{ color: sysStats?.crawler?.enabled ? "#52c41a" : "#999" }} />
          </Card>
        </Col>
      </Row>

      <Card title={<><UserOutlined /> 当前管理员</>} style={{ maxWidth: 600, marginBottom: 16 }}>
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <div>
            <Tag color="blue">已登录</Tag>
            <span style={{ marginLeft: 8, fontSize: 16 }}>
              {currentUser.display_name || currentUser.username}
            </span>
            {currentUser.is_admin && <Tag color="gold" style={{ marginLeft: 8 }}>管理员</Tag>}
          </div>
          <Table
            dataSource={[
              { key: "ID", value: currentUser.id },
              { key: "用户名", value: currentUser.username },
              { key: "显示名称", value: currentUser.display_name || "—" },
              { key: "角色", value: currentUser.is_admin ? "管理员" : "普通用户" },
            ]}
            columns={[
              { title: "字段", dataIndex: "key", width: 120 },
              { title: "值", dataIndex: "value", render: (v) => (typeof v === "boolean" ? (v ? "✅是" : "❌否") : v) },
            ]}
            pagination={false}
            size="small"
          />
          <Button danger icon={<LogoutOutlined />} onClick={handleLogout}>退出登录</Button>
        </Space>
      </Card>

      <Card title={<><ApiOutlined /> API 接口列表</>} style={{ maxWidth: 600 }}>
        <Table
          dataSource={[
            { method: "POST", path: "/api/v1/auth/login", desc: "用户登录" },
            { method: "GET", path: "/api/v1/auth/me", desc: "当前用户信息" },
            { method: "POST", path: "/api/v1/auth/change-password", desc: "修改密码" },
            { method: "GET", path: "/api/v1/health", desc: "健康检查" },
            { method: "GET", path: "/api/v1/announcements", desc: "招标公告列表" },
            { method: "GET", path: "/api/v1/awards", desc: "中标结果" },
            { method: "GET", path: "/api/v1/overview/today", desc: "今日概览" },
            { method: "GET", path: "/docs", desc: "Swagger API 文档" },
          ]}
          columns={[
            { title: "方法", dataIndex: "method", width: 70, render: (m) => <Tag color={m === "GET" ? "green" : "blue"}>{m}</Tag> },
            { title: "路径", dataIndex: "path", width: 280 },
            { title: "说明", dataIndex: "desc" },
          ]}
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  );
}

export default Admin;
