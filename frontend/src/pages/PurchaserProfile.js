import React, { useState, useEffect, useCallback } from "react";
import {
  Card, Row, Col, Select, Statistic, Tag, Table, Progress,
  Typography, Spin, Empty, Alert, Divider, Space, Tooltip,
} from "antd";
import {
  TrophyOutlined, RiseOutlined, TeamOutlined,
  BulbOutlined, StarOutlined, StarFilled, WarningOutlined,
  CheckCircleOutlined, ClockCircleOutlined, BankOutlined,
  CrownOutlined,
} from "@ant-design/icons";
import { getPurchasers, getPurchaserProfile } from "../services/api";

const { Title, Text, Paragraph } = Typography;

// ============================================================
// 柱状图（纯 CSS）
// ============================================================

function SimpleBarChart({ data, maxValue }) {
  if (!data || data.length === 0) return <Empty description="暂无数据" />;
  const max = maxValue || Math.max(...data.map(d => d.win_count), 1);
  const colors = ["#1677ff", "#52c41a", "#fa8c16", "#eb2f96", "#722ed1", "#13c2c2", "#f5222d", "#2f54eb", "#faad14", "#a0d911"];

  return (
    <div style={{ padding: "8px 0" }}>
      {data.map((item, idx) => (
        <div key={idx} style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
          <Text style={{ width: 140, fontSize: 12, textAlign: "right", marginRight: 8, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {item.name}
          </Text>
          <div style={{ flex: 1, background: "#f5f5f5", borderRadius: 4, height: 22, position: "relative" }}>
            <div style={{
              width: `${(item.win_count / max) * 100}%`,
              height: "100%",
              background: colors[idx % colors.length],
              borderRadius: 4,
              transition: "width 0.6s ease",
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-end",
              paddingRight: 6,
              minWidth: item.win_count > 0 ? 30 : 0,
            }}>
              <Text strong style={{ color: "#fff", fontSize: 11 }}>{item.win_count}次</Text>
            </div>
          </div>
          <Text type="secondary" style={{ width: 50, fontSize: 11, marginLeft: 8 }}>{item.percentage}%</Text>
        </div>
      ))}
    </div>
  );
}

// ============================================================
// 在位者赛道表格
// ============================================================

const CATEGORY_COLORS = {
  "品牌策略类": "magenta", "创意设计类": "purple",
  "媒介投放类": "cyan", "活动执行类": "orange",
  "内容制作类": "geekblue", "新媒体运营类": "green",
};

function IncumbentTable({ incumbentMap }) {
  if (!incumbentMap || Object.keys(incumbentMap).length === 0) {
    return <Empty description="暂无在位者数据" />;
  }

  const columns = [
    {
      title: "赛道",
      dataIndex: "category",
      key: "category",
      width: 130,
      render: (cat) => <Tag color={CATEGORY_COLORS[cat]}>{cat.replace("类", "")}</Tag>,
    },
    {
      title: "在位者",
      dataIndex: "company",
      key: "company",
      render: (company) =>
        company ? (
          <Space>
            <CrownOutlined style={{ color: "#faad14" }} />
            <Text strong>{company}</Text>
          </Space>
        ) : (
          <Tag color="green" icon={<CheckCircleOutlined />}>
            暂无在位者（机会窗口）
          </Tag>
        ),
    },
    {
      title: "合同到期",
      dataIndex: "contract_end",
      key: "contract_end",
      width: 120,
      render: (date) => {
        if (!date) return <Text type="secondary">—</Text>;
        const days = Math.ceil((new Date(date) - new Date()) / (1000 * 60 * 60 * 24));
        if (days < 0) return <Tag color="default">已过期</Tag>;
        if (days <= 90) return <Tag color="orange">{date} (剩余{days}天)</Tag>;
        return <Text>{date}</Text>;
      },
    },
  ];

  const dataSource = Object.entries(incumbentMap).map(([cat, info], idx) => ({
    key: idx,
    category: cat,
    company: info?.company || null,
    contract_end: info?.contract_end || null,
  }));

  return (
    <Table
      columns={columns}
      dataSource={dataSource}
      pagination={false}
      size="small"
    />
  );
}

// ============================================================
// 主组件
// ============================================================

function PurchaserProfile() {
  const [purchasers, setPurchasers] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);

  // 加载采购方列表
  useEffect(() => {
    getPurchasers()
      .then(data => {
        const list = Array.isArray(data) ? data : data?.items || [];
        setPurchasers(list);
        if (list.length > 0 && !selectedId) {
          setSelectedId(list[0].id || list[0].purchaser_id);
        }
      })
      .catch(() => {
        console.error("获取采购方列表失败");
        setPurchasers([]);
      });
  }, []);

  // 加载画像
  const loadProfile = useCallback(async (id) => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await getPurchaserProfile(id);
      setProfile(data);
    } catch {
      console.error("获取采购方画像失败");
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, [purchasers]);

  useEffect(() => {
    if (selectedId) loadProfile(selectedId);
  }, [selectedId, loadProfile]);

  const purchaserOptions = purchasers.map(p => ({
    value: p.id || p.purchaser_id,
    label: `${p.name || p.purchaser_name} ${p.level ? `(${p.level})` : ""}`,
  }));

  // 集中度标签颜色
  const concentrationColor = {
    "分散": "green", "中度集中": "orange", "高度集中": "red",
  };

  return (
    <div>
      {/* 标题 + 选择器 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 20 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <BankOutlined /> 采购方画像分析
          </Title>
        </Col>
        <Col>
          <Select
            showSearch
            value={selectedId}
            onChange={setSelectedId}
            options={purchaserOptions}
            style={{ width: 280 }}
            placeholder="选择采购方..."
            filterOption={(input, option) =>
              option.label.toLowerCase().includes(input.toLowerCase())
            }
          />
        </Col>
      </Row>

      <Spin spinning={loading}>
        {profile ? (
          <>
            {/* ── 概览卡片 ── */}
            <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
              <Col xs={24} sm={12} md={6}>
                <Card size="small">
                  <Statistic
                    title="近1年广告项目"
                    value={profile.supplier_top10?.reduce((s, x) => s + x.win_count, 0) || 0}
                    prefix={<TrophyOutlined />}
                    valueStyle={{ color: "#1677ff" }}
                    suffix="个"
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card size="small">
                  <Statistic
                    title="HHI 集中度"
                    value={profile.hhi_index || 0}
                    prefix={<RiseOutlined />}
                    suffix={
                      <Tag
                        color={concentrationColor[profile.concentration_level] || "default"}
                        style={{ marginLeft: 8 }}
                      >
                        {profile.concentration_level}
                      </Tag>
                    }
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card size="small">
                  <Statistic
                    title="中小公司占比"
                    value={profile.sme_win_rate || 0}
                    prefix={<TeamOutlined />}
                    suffix="%"
                    valueStyle={{
                      color: (profile.sme_win_rate || 0) >= 25 ? "#52c41a" :
                             (profile.sme_win_rate || 0) >= 15 ? "#faad14" : "#ff4d4f",
                    }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card size="small">
                  <Statistic
                    title="机会评级"
                    value={profile.opportunity_rating || "★★"}
                    prefix={<StarFilled style={{ color: "#faad14" }} />}
                  />
                </Card>
              </Col>
            </Row>

            {/* ── 供应商Top10 + 在位者地图 ── */}
            <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
              <Col xs={24} lg={14}>
                <Card
                  title={<><TrophyOutlined /> 供应商 Top10（按中标次数）</>}
                  size="small"
                >
                  <SimpleBarChart
                    data={profile.supplier_top10 || []}
                  />
                </Card>
              </Col>
              <Col xs={24} lg={10}>
                <Card
                  title={<><CrownOutlined /> 各赛道在位者</>}
                  size="small"
                >
                  <IncumbentTable incumbentMap={profile.incumbent_map} />
                </Card>
              </Col>
            </Row>

            {/* ── 中小公司机会分析 ── */}
            <Card
              title={<><BulbOutlined /> 中小公司机会分析</>}
              size="small"
            >
              <Row gutter={[24, 16]}>
                <Col xs={24} sm={8}>
                  <Statistic
                    title="近2年新进入者"
                    value={profile.new_entrant_count || 0}
                    prefix={<TeamOutlined />}
                    suffix="家"
                  />
                </Col>
                <Col xs={24} sm={8}>
                  <div>
                    <Text type="secondary">破圈案例</Text>
                    <div style={{ marginTop: 8 }}>
                      {profile.has_breakthrough_case ? (
                        <Tag color="green" icon={<CheckCircleOutlined />}>
                          有破圈案例 — 新进入者有机会
                        </Tag>
                      ) : (
                        <Tag color="orange" icon={<WarningOutlined />}>
                          暂无破圈 — 头部公司垄断
                        </Tag>
                      )}
                    </div>
                  </div>
                </Col>
                <Col xs={24} sm={8}>
                  <div>
                    <Text type="secondary">机会窗口赛道</Text>
                    <div style={{ marginTop: 8 }}>
                      {profile.incumbent_map &&
                        Object.entries(profile.incumbent_map)
                          .filter(([, v]) => !v?.company)
                          .map(([cat]) => (
                            <Tag key={cat} color="green" style={{ marginBottom: 4 }}>
                              {cat.replace("类", "")}
                            </Tag>
                          ))}
                      {profile.incumbent_map &&
                        Object.values(profile.incumbent_map).every(v => v?.company) && (
                          <Text type="secondary">暂无明显机会窗口</Text>
                        )}
                    </div>
                  </div>
                </Col>
              </Row>

              <Divider style={{ margin: "16px 0" }} />

              <Alert
                type={profile.opportunity_rating?.length >= 5 ? "success" :
                      profile.opportunity_rating?.length >= 4 ? "info" :
                      profile.opportunity_rating?.length >= 3 ? "warning" : "error"}
                message={
                  profile.opportunity_rating?.length >= 5
                    ? "🌟 极佳机会：中小公司中标占比高且有破圈案例，建议重点关注此采购方。"
                    : profile.opportunity_rating?.length >= 4
                    ? "👍 较好机会：中小公司中标占比适中，有突围空间。"
                    : profile.opportunity_rating?.length >= 3
                    ? "👀 一般机会：竞争较为集中，但仍有参与机会。建议准备差异化方案。"
                    : "⚠️ 机会有限：头部公司高度垄断，新进入者需谨慎评估投入产出。"
                }
                showIcon
              />
            </Card>
          </>
        ) : (
          <Empty description="请选择一个采购方查看画像" />
        )}
      </Spin>
    </div>
  );
}

export default PurchaserProfile;
