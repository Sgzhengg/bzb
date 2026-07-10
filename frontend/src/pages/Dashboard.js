import React, { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Typography, Tag, Table, Space, Button, Spin, Empty } from "antd";
import {
  FileTextOutlined, BellOutlined, StarOutlined,
  RiseOutlined, ThunderboltOutlined, ArrowRightOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useDashboardStats, useChartData, useFavorites } from "../services/apiHooks";

const { Title, Text } = Typography;

// ============================================================
// 简单柱状图（纯 CSS）
// ============================================================

function MiniBarChart({ data, title }) {
  if (!data || data.length === 0) return <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  const maxVal = Math.max(...data.map(d => d.value), 1);
  const colors = ["#1677ff", "#52c41a", "#fa8c16", "#eb2f96", "#722ed1", "#13c2c2"];

  return (
    <div>
      <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: "block" }}>{title}</Text>
      {data.slice(0, 6).map((item, idx) => (
        <div key={idx} style={{ display: "flex", alignItems: "center", marginBottom: 5 }}>
          <Text style={{ width: 70, fontSize: 11, textAlign: "right", marginRight: 6, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {item.label}
          </Text>
          <div style={{ flex: 1, background: "#f5f5f5", borderRadius: 3, height: 16 }}>
            <div style={{
              width: `${Math.max((item.value / maxVal) * 100, 5)}%`, height: "100%",
              background: colors[idx % colors.length], borderRadius: 3,
              display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 4,
            }}>
              <Text style={{ color: "#fff", fontSize: 10 }}>{item.value}</Text>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ============================================================
// 主组件
// ============================================================

function Dashboard() {
  const navigate = useNavigate();

  // 使用 React Query hooks
  const { unreadAlerts, recentAnnouncements, isLoading: statsLoading } = useDashboardStats();
  const { data: cityChart = [], isLoading: chartLoading } = useChartData("city_comparison", { top_n: 10 });
  const { data: favData = { items: [] }, isLoading: favLoading } = useFavorites({ page_size: 5 });

  // 转换图表数据格式
  const cityData = cityChart.data?.map(d => ({
    label: d.city || d.name || "",
    value: d.count || d.value || 0
  })) || [];

  const favorites = favData.items || [];
  const loading = statsLoading || chartLoading || favLoading;

  const announcementTotal = recentAnnouncements.length || 0;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>📊 数据看板</Title>
        <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => navigate("/opportunities")}>
          查看全部机会
        </Button>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card hoverable onClick={() => navigate("/opportunities")}>
            <Statistic
              title="最新公告"
              value={announcementTotal}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: "#1677ff" }}
              suffix={<Text type="secondary" style={{ fontSize: 14 }}>条</Text>}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card hoverable onClick={() => navigate("/client-relations")}>
            <Statistic
              title="未读提醒"
              value={unreadAlerts}
              prefix={<BellOutlined />}
              valueStyle={{ color: unreadAlerts > 0 ? "#ff4d4f" : "#52c41a" }}
              suffix={<Text type="secondary" style={{ fontSize: 14 }}>条</Text>}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card hoverable onClick={() => navigate("/opportunities")}>
            <Statistic
              title="收藏项目"
              value={favorites.length}
              prefix={<StarOutlined />}
              valueStyle={{ color: "#faad14" }}
              suffix={<Text type="secondary" style={{ fontSize: 14 }}>个</Text>}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card hoverable onClick={() => navigate("/region-compare")}>
            <Statistic
              title="覆盖地市"
              value={cityData.length}
              prefix={<RiseOutlined />}
              valueStyle={{ color: "#722ed1" }}
              suffix={<Text type="secondary" style={{ fontSize: 14 }}>个</Text>}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表 + 列表 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={10}>
          <Card title="🏙️ 地市项目分布" extra={
            <Button type="link" size="small" onClick={() => navigate("/region-compare")}>
              详情 <ArrowRightOutlined />
            </Button>
          }>
            {cityData.length > 0 ? (
              <MiniBarChart data={cityData} title="" />
            ) : (
              <Empty description="暂无数据，请先触发数据采集" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={14}>
          <Card title="⭐ 我的收藏" extra={
            <Button type="link" size="small" onClick={() => navigate("/opportunities")}>
              查看全部 <ArrowRightOutlined />
            </Button>
          }>
            {favorites.length > 0 ? (
              favorites.map((item, idx) => (
                <div
                  key={item.id}
                  onClick={() => navigate(`/opportunities/${item.id}`)}
                  style={{
                    padding: "8px 0", borderBottom: idx < favorites.length - 1 ? "1px solid #f0f0f0" : "none",
                    cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between",
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <Text strong ellipsis style={{ maxWidth: 300, display: "inline-block" }}>
                      {item.title}
                    </Text>
                    <div>
                      <Tag color="blue" style={{ fontSize: 11 }}>{item.project_category}</Tag>
                      <Text type="secondary" style={{ fontSize: 11 }}>{item.announce_date}</Text>
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <Text strong style={{ color: "#1677ff" }}>
                      {item.budget != null ? `${item.budget}万` : "—"}
                    </Text>
                    {item.total_score != null && (
                      <div>
                        <Tag color={item.total_score >= 75 ? "success" : item.total_score >= 50 ? "warning" : "error"}>
                          {Math.round(item.total_score)}分
                        </Tag>
                      </div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <Empty description="暂无收藏项目" image={Empty.PRESENTED_IMAGE_SIMPLE}>
                <Button type="primary" onClick={() => navigate("/opportunities")}>
                  去发现机会
                </Button>
              </Empty>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default Dashboard;
