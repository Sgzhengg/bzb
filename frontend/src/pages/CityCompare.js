import React, { useState, useEffect, useMemo } from "react";
import {
  Card, Table, Tag, Typography, Row, Col, Spin, Empty, Progress, Statistic,
} from "antd";
import {
  RiseOutlined, TrophyOutlined, TeamOutlined, EnvironmentOutlined,
} from "@ant-design/icons";

const { Title, Text } = Typography;

// Mock fallback data
const MOCK_CITIES = [
  { city: "广州", recent_project_count: 18, total_project_count: 42, head_supplier_ratio: 35.7, incumbent_renewal_rate: 62.5, sme_win_rate: 28.5, opportunity_rating: "★★★★☆", advice: "👍 建议重点关注：竞争环境较好，有突围空间", purchaser_id: 2 },
  { city: "深圳", recent_project_count: 15, total_project_count: 35, head_supplier_ratio: 42.1, incumbent_renewal_rate: 55.0, sme_win_rate: 32.0, opportunity_rating: "★★★★★", advice: "🌟 推荐优先切入：项目多、中小公司活跃、在位者不稳固", purchaser_id: 3 },
  { city: "东莞", recent_project_count: 12, total_project_count: 28, head_supplier_ratio: 28.6, incumbent_renewal_rate: 40.0, sme_win_rate: 38.2, opportunity_rating: "★★★★★", advice: "🌟 推荐优先切入：项目多、中小公司活跃、在位者不稳固", purchaser_id: 4 },
  { city: "佛山", recent_project_count: 10, total_project_count: 22, head_supplier_ratio: 50.0, incumbent_renewal_rate: 70.0, sme_win_rate: 15.8, opportunity_rating: "★★★☆☆", advice: "👀 可选择性参与：需评估自身优势匹配度", purchaser_id: 5 },
  { city: "珠海", recent_project_count: 6, total_project_count: 12, head_supplier_ratio: 60.0, incumbent_renewal_rate: 75.0, sme_win_rate: 8.3, opportunity_rating: "★★☆☆☆", advice: "⚠️ 谨慎参与：竞争较为激烈，在位者优势明显", purchaser_id: 6 },
  { city: "中山", recent_project_count: 8, total_project_count: 18, head_supplier_ratio: 45.0, incumbent_renewal_rate: 55.0, sme_win_rate: 22.0, opportunity_rating: "★★★☆☆", advice: "👀 可选择性参与：需评估自身优势匹配度", purchaser_id: 7 },
  { city: "惠州", recent_project_count: 5, total_project_count: 10, head_supplier_ratio: 70.0, incumbent_renewal_rate: 80.0, sme_win_rate: 10.0, opportunity_rating: "★★☆☆☆", advice: "⚠️ 谨慎参与：竞争较为激烈，在位者优势明显", purchaser_id: 8 },
  { city: "汕头", recent_project_count: 4, total_project_count: 8, head_supplier_ratio: 75.0, incumbent_renewal_rate: 85.0, sme_win_rate: 12.5, opportunity_rating: "★☆☆☆☆", advice: "❌ 不建议投入：项目少且头部垄断严重", purchaser_id: 9 },
  { city: "江门", recent_project_count: 3, total_project_count: 6, head_supplier_ratio: 80.0, incumbent_renewal_rate: 90.0, sme_win_rate: 5.0, opportunity_rating: "★☆☆☆☆", advice: "❌ 不建议投入：项目少且头部垄断严重", purchaser_id: 10 },
  { city: "湛江", recent_project_count: 2, total_project_count: 5, head_supplier_ratio: 85.0, incumbent_renewal_rate: 95.0, sme_win_rate: 0.0, opportunity_rating: "★☆☆☆☆", advice: "❌ 不建议投入：项目少且头部垄断严重", purchaser_id: 11 },
  { city: "茂名", recent_project_count: 3, total_project_count: 7, head_supplier_ratio: 65.0, incumbent_renewal_rate: 70.0, sme_win_rate: 14.3, opportunity_rating: "★★☆☆☆", advice: "⚠️ 谨慎参与：竞争较为激烈，在位者优势明显", purchaser_id: 12 },
  { city: "肇庆", recent_project_count: 4, total_project_count: 9, head_supplier_ratio: 55.0, incumbent_renewal_rate: 60.0, sme_win_rate: 22.2, opportunity_rating: "★★★☆☆", advice: "👀 可选择性参与：需评估自身优势匹配度", purchaser_id: 13 },
  { city: "梅州", recent_project_count: 2, total_project_count: 4, head_supplier_ratio: 90.0, incumbent_renewal_rate: 100.0, sme_win_rate: 0.0, opportunity_rating: "★☆☆☆☆", advice: "❌ 不建议投入：项目少且头部垄断严重", purchaser_id: 14 },
  { city: "汕尾", recent_project_count: 1, total_project_count: 3, head_supplier_ratio: 100.0, incumbent_renewal_rate: 100.0, sme_win_rate: 0.0, opportunity_rating: "★☆☆☆☆", advice: "❌ 不建议投入：项目少且头部垄断严重", purchaser_id: 15 },
  { city: "河源", recent_project_count: 2, total_project_count: 4, head_supplier_ratio: 75.0, incumbent_renewal_rate: 80.0, sme_win_rate: 25.0, opportunity_rating: "★★★☆☆", advice: "👀 可选择性参与：需评估自身优势匹配度", purchaser_id: 16 },
  { city: "阳江", recent_project_count: 3, total_project_count: 6, head_supplier_ratio: 60.0, incumbent_renewal_rate: 65.0, sme_win_rate: 16.7, opportunity_rating: "★★★☆☆", advice: "👀 可选择性参与：需评估自身优势匹配度", purchaser_id: 17 },
  { city: "清远", recent_project_count: 2, total_project_count: 5, head_supplier_ratio: 70.0, incumbent_renewal_rate: 75.0, sme_win_rate: 20.0, opportunity_rating: "★★★☆☆", advice: "👀 可选择性参与：需评估自身优势匹配度", purchaser_id: 18 },
  { city: "潮州", recent_project_count: 1, total_project_count: 3, head_supplier_ratio: 100.0, incumbent_renewal_rate: 100.0, sme_win_rate: 0.0, opportunity_rating: "★☆☆☆☆", advice: "❌ 不建议投入：项目少且头部垄断严重", purchaser_id: 19 },
  { city: "揭阳", recent_project_count: 2, total_project_count: 4, head_supplier_ratio: 80.0, incumbent_renewal_rate: 85.0, sme_win_rate: 25.0, opportunity_rating: "★★★☆☆", advice: "👀 可选择性参与：需评估自身优势匹配度", purchaser_id: 20 },
  { city: "云浮", recent_project_count: 1, total_project_count: 2, head_supplier_ratio: 100.0, incumbent_renewal_rate: 100.0, sme_win_rate: 0.0, opportunity_rating: "★☆☆☆☆", advice: "❌ 不建议投入：项目少且头部垄断严重", purchaser_id: 21 },
  { city: "韶关", recent_project_count: 2, total_project_count: 4, head_supplier_ratio: 75.0, incumbent_renewal_rate: 80.0, sme_win_rate: 25.0, opportunity_rating: "★★★☆☆", advice: "👀 可选择性参与：需评估自身优势匹配度", purchaser_id: 22 },
];

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
        .catch(() => setData(MOCK_CITIES))
        .finally(() => setLoading(false));
    }).catch(() => {
      setData(MOCK_CITIES);
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
