import React, { useState, useEffect, useMemo } from "react";
import {
  Card, Table, Tag, Typography, Row, Col, Spin, Empty, Progress, Statistic,
} from "antd";
import {
  RiseOutlined, TrophyOutlined, TeamOutlined, EnvironmentOutlined,
} from "@ant-design/icons";

const { Title, Text } = Typography;

// 简单柱状图
function SMEScoreBar({ data }) {
  if (!data || data.length === 0) return <Empty description="暂无数据" />;
  const sorted = [...data].sort((a, b) => b.sme_win_rate - a.sme_win_rate);
  const maxVal = Math.max(...sorted.map(d => d.sme_win_rate), 1);

  return (
    <div style={{ padding: "8px 0" }}>
      {sorted.map((item, idx) => (
        <div key={idx} style={{ display: "flex", alignItems: "center", marginBottom: 6 }}>
          <Text style={{ width: 50, fontSize: 11, textAlign: "right", marginRight: 6 }}>{item.city}</Text>
          <div style={{ flex: 1, background: "#f5f5f5", borderRadius: 3, height: 18 }}>
            <div style={{
              width: `${(item.sme_win_rate / maxVal) * 100}%`, height: "100%",
              background: item.sme_win_rate >= 25 ? "#52c41a" : item.sme_win_rate >= 15 ? "#faad14" : "#ff4d4f",
              borderRadius: 3, transition: "width 0.6s",
              display: "flex", alignItems: "center", justifyContent: "flex-end",
              paddingRight: 6, minWidth: item.sme_win_rate > 0 ? 28 : 0,
            }}>
              <Text strong style={{ color: "#fff", fontSize: 10 }}>{item.sme_win_rate}%</Text>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function CityCompare({ onNavigate }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    import("../services/api").then(({ default: api }) => {
      api.get("/purchasers/compare")
        .then(res => setData(res?.items || []))
        .catch(() => {
          console.error("获取地市对比数据失败");
          setData([]);
        })
        .finally(() => setLoading(false));
    }).catch(() => {
      console.error("加载API模块失败");
      setData([]);
      setLoading(false);
    });
  }, []);

  const stats = useMemo(() => {
    const total = data.reduce((s, x) => s + x.recent_project_count, 0);
    const avgSme = data.length > 0 ? data.reduce((s, x) => s + x.sme_win_rate, 0) / data.length : 0;
    const topCities = data.filter(d => d.opportunity_rating?.includes("★★★★★"));
    return { total, avgSme: avgSme.toFixed(1), topCount: topCities.length };
  }, [data]);

  const columns = [
    {
      title: "地市", dataIndex: "city", key: "city", width: 80, fixed: "left",
      render: (city, record) => (
        <a onClick={() => onNavigate?.("profile", record.purchaser_id)}>
          <EnvironmentOutlined style={{ marginRight: 4 }} />{city}
        </a>
      ),
    },
    {
      title: "近1年项目", dataIndex: "recent_project_count", key: "recent", width: 100,
      sorter: (a, b) => a.recent_project_count - b.recent_project_count,
      render: v => <Text strong>{v}</Text>,
    },
    {
      title: "头部集中度", dataIndex: "head_supplier_ratio", key: "head", width: 110,
      sorter: (a, b) => a.head_supplier_ratio - b.head_supplier_ratio,
      render: v => <Progress percent={v} size="small" strokeColor={v > 60 ? "#ff4d4f" : v > 40 ? "#faad14" : "#52c41a"} format={p => `${p}%`} />,
    },
    {
      title: "在位者续约率", dataIndex: "incumbent_renewal_rate", key: "renewal", width: 120,
      sorter: (a, b) => a.incumbent_renewal_rate - b.incumbent_renewal_rate,
      render: v => {
        const color = v > 70 ? "#ff4d4f" : v > 50 ? "#faad14" : "#52c41a";
        return <Tag color={color}>{v}%</Tag>;
      },
    },
    {
      title: "中小公司占比", dataIndex: "sme_win_rate", key: "sme", width: 120,
      sorter: (a, b) => a.sme_win_rate - b.sme_win_rate,
      defaultSortOrder: "descend",
      render: v => {
        const color = v >= 25 ? "#52c41a" : v >= 15 ? "#faad14" : "#ff4d4f";
        return <Progress percent={v} size="small" strokeColor={color} format={p => `${p}%`} />;
      },
    },
    {
      title: "机会评级", dataIndex: "opportunity_rating", key: "rating", width: 130,
      sorter: (a, b) => (a.opportunity_rating || "").length - (b.opportunity_rating || "").length,
      render: v => <Text style={{ color: "#faad14", fontSize: 14, letterSpacing: 2 }}>{v}</Text>,
    },
    {
      title: "建议", dataIndex: "advice", key: "advice", ellipsis: true,
      render: v => <Text type="secondary" style={{ fontSize: 12 }}>{v}</Text>,
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>
        <EnvironmentOutlined /> 地市对比看板
      </Title>

      {/* 概览统计 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic title="近1年广告项目总数" value={stats.total}
              prefix={<TrophyOutlined />} suffix="个" valueStyle={{ color: "#1677ff" }} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic title="平均中小公司占比" value={stats.avgSme}
              prefix={<TeamOutlined />} suffix="%" valueStyle={{ color: "#52c41a" }} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic title="优先切入地市数" value={stats.topCount}
              prefix={<RiseOutlined />} suffix="个(★★★★★)" valueStyle={{ color: "#fa8c16" }} />
          </Card>
        </Col>
      </Row>

      {/* 柱状图 + 表格 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card title={<><TeamOutlined /> 中小公司中标占比排名</>} size="small">
            <SMEScoreBar data={data} />
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card size="small">
            <Spin spinning={loading}>
              {data.length === 0 && !loading ? (
                <Empty description="暂无地市对比数据" />
              ) : (
                <Table
                  columns={columns}
                  dataSource={data}
                  rowKey="city"
                  pagination={false}
                  scroll={{ x: 900 }}
                  size="middle"
                />
              )}
            </Spin>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default CityCompare;
