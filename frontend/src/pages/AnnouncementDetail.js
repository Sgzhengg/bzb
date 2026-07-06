import React, { useState, useEffect, useCallback } from "react";
import {
  Card, Descriptions, Tag, Typography, Spin, Empty, Button, Space,
  Row, Col, Progress, Divider, Table, Alert, message, Tooltip, Badge,
} from "antd";
import {
  ArrowLeftOutlined, StarOutlined, StarFilled, LinkOutlined,
  ClockCircleOutlined, WarningOutlined, CheckCircleOutlined,
  CrownOutlined, TeamOutlined, PhoneOutlined, MailOutlined,
} from "@ant-design/icons";
import { useParams, useNavigate } from "react-router-dom";
import {
  getAnnouncementDetail, getAnnouncementAlerts,
  toggleFavorite, markAlertRead,
} from "../services/api";

const { Title, Text, Paragraph } = Typography;

// ============================================================
// 常量
// ============================================================

const PROCUREMENT_COLORS = {
  "公开招标": "blue", "公开询比": "green",
  "竞争性谈判": "orange", "单一来源": "red",
};
const PROB_COLORS = { "低": "#52c41a", "中": "#faad14", "高": "#ff4d4f" };
const SCORE_LABELS = {
  procurement_fairness: "采购公平性",
  hhi_concentration: "竞争集中度",
  category_match: "赛道匹配度",
  budget_health: "预算健康度",
  incumbent_advantage: "在位者优势",
  client_relation: "客情关系",
};

// ============================================================
// 评分雷达卡片
// ============================================================

function ScoreCard({ detailScores }) {
  if (!detailScores || Object.keys(detailScores).length === 0) {
    return <Empty description="暂无评分数据" />;
  }
  const items = Object.entries(detailScores).map(([key, val]) => ({
    key, label: SCORE_LABELS[key] || key, value: Math.round(val || 0),
  }));
  const colors = ["#1677ff", "#52c41a", "#fa8c16", "#eb2f96", "#722ed1", "#13c2c2"];

  return (
    <div>
      {items.map((item, idx) => (
        <div key={item.key} style={{ marginBottom: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <Text style={{ fontSize: 13 }}>{item.label}</Text>
            <Text strong style={{ color: colors[idx % colors.length] }}>{item.value}分</Text>
          </div>
          <Progress
            percent={item.value}
            strokeColor={colors[idx % colors.length]}
            showInfo={false}
            size="small"
          />
        </div>
      ))}
    </div>
  );
}

// ============================================================
// 在位者卡片
// ============================================================

function IncumbentCard({ info }) {
  if (!info) return <Empty description="无在位者数据" />;
  const riskColors = { "高": "red", "中": "orange", "低": "green", "无": "default" };

  return (
    <Card size="small" style={{ marginBottom: 12 }}>
      {info.has_incumbent ? (
        <div>
          <div style={{ marginBottom: 8 }}>
            <CrownOutlined style={{ color: "#faad14", marginRight: 6 }} />
            <Text strong style={{ fontSize: 15 }}>{info.incumbent_name}</Text>
            <Tag color={riskColors[info.risk_level]} style={{ marginLeft: 8 }}>
              {info.risk_level}风险
            </Tag>
          </div>
          <Text type="secondary">
            连续中标 {info.continuous_count} 次 · {info.reason}
          </Text>
        </div>
      ) : (
        <div>
          <CheckCircleOutlined style={{ color: "#52c41a", marginRight: 6 }} />
          <Text style={{ color: "#52c41a" }}>暂未检测到在位者，机会窗口打开</Text>
          <br />
          <Text type="secondary" style={{ fontSize: 12 }}>{info.reason}</Text>
        </div>
      )}
    </Card>
  );
}

// ============================================================
// 主组件
// ============================================================

function AnnouncementDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [alerts, setAlerts] = useState([]);
  const [isFav, setIsFav] = useState(false);

  const loadDetail = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getAnnouncementDetail(id);
      setData(result);
      setIsFav(result.is_favorited || false);
    } catch {
      message.error("加载公告详情失败");
    } finally {
      setLoading(false);
    }
  }, [id]);

  const loadAlerts = useCallback(async () => {
    try {
      const result = await getAnnouncementAlerts(id);
      setAlerts(result?.items || []);
    } catch { /* ignore */ }
  }, [id]);

  useEffect(() => { loadDetail(); loadAlerts(); }, [loadDetail, loadAlerts]);

  const handleFavorite = async () => {
    try {
      const result = await toggleFavorite(id);
      setIsFav(result.is_favorited);
      message.success(result.message);
    } catch {
      message.error("操作失败");
    }
  };

  const handleMarkRead = async (alertId) => {
    try {
      await markAlertRead(alertId);
      setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, is_read: true } : a));
    } catch { /* ignore */ }
  };

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (!data) return <Empty description="公告不存在" />;

  const score = data.total_score;
  const probLabel = data.probability_label;

  return (
    <div>
      {/* 返回 + 操作栏 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/opportunities")}>
          返回列表
        </Button>
        <Space>
          <Tooltip title={isFav ? "取消收藏" : "收藏"}>
            <Button
              icon={isFav ? <StarFilled style={{ color: "#faad14" }} /> : <StarOutlined />}
              onClick={handleFavorite}
              type={isFav ? "primary" : "default"}
            >
              {isFav ? "已收藏" : "收藏"}
            </Button>
          </Tooltip>
        </Space>
      </div>

      {/* 标题 + 评分 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 280 }}>
            <Title level={4} style={{ marginTop: 0 }}>{data.title}</Title>
            <Space wrap size={[8, 8]}>
              <Tag color="blue">{data.purchaser}</Tag>
              <Tag color={PROCUREMENT_COLORS[data.procurement_method]}>
                {data.procurement_method}
              </Tag>
              <Tag color="purple">{data.project_category}</Tag>
              {data.source_url && (
                <a href={data.source_url} target="_blank" rel="noreferrer">
                  <Tag icon={<LinkOutlined />} color="geekblue">原文链接</Tag>
                </a>
              )}
            </Space>
          </div>
          <div style={{ textAlign: "center", minWidth: 140, marginTop: 8 }}>
            <div style={{ fontSize: 40, fontWeight: "bold", color: PROB_COLORS[probLabel] || "#1677ff" }}>
              {score != null ? Math.round(score) : "—"}
            </div>
            <Text type="secondary">综合评分</Text>
            <br />
            <Tag color={PROB_COLORS[probLabel] || "default"} style={{ marginTop: 4 }}>
              陪跑概率: {probLabel || "—"}
            </Tag>
          </div>
        </div>
        {data.recommendation && (
          <Alert message={data.recommendation} type={probLabel === "低" ? "success" : probLabel === "中" ? "warning" : "error"} style={{ marginTop: 12 }} showIcon />
        )}
      </Card>

      <Row gutter={[16, 16]}>
        {/* 左侧：基本信息 + 评分 */}
        <Col xs={24} lg={14}>
          <Card title="📋 基本信息" style={{ marginBottom: 16 }}>
            <Descriptions column={{ xs: 1, sm: 2 }} size="small" bordered>
              <Descriptions.Item label="采购方">{data.purchaser}</Descriptions.Item>
              <Descriptions.Item label="层级">{data.purchaser_level}</Descriptions.Item>
              <Descriptions.Item label="项目类别">{data.project_category}</Descriptions.Item>
              <Descriptions.Item label="采购方式">
                <Tag color={PROCUREMENT_COLORS[data.procurement_method]}>{data.procurement_method}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="预算金额">
                <Text strong style={{ fontSize: 16, color: "#1677ff" }}>
                  {data.budget != null ? `${data.budget} 万元` : "—"}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="公告日期">{data.announce_date || "—"}</Descriptions.Item>
              <Descriptions.Item label="投标截止">
                <ClockCircleOutlined style={{ marginRight: 4 }} />
                {data.deadline || "—"}
              </Descriptions.Item>
              <Descriptions.Item label="资格要求">
                <Paragraph ellipsis={{ rows: 2, expandable: true }}>
                  {data.qualification_requirements || "—"}
                </Paragraph>
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {/* 评分明细 */}
          <Card title="📊 评分明细">
            <ScoreCard detailScores={data.detail_scores} />
          </Card>
        </Col>

        {/* 右侧：在位者 + 提醒 + 历史 */}
        <Col xs={24} lg={10}>
          {/* 在位者 */}
          <Card title={<><CrownOutlined /> 在位者检测</>} style={{ marginBottom: 16 }}>
            <IncumbentCard info={data.incumbent_info} />
          </Card>

          {/* 客情提醒 */}
          <Card
            title={<><BellOutlined /> 客情提醒 ({alerts.length})</>}
            style={{ marginBottom: 16 }}
          >
            {alerts.length === 0 ? (
              <Empty description="暂无关联提醒" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              alerts.map(a => (
                <Alert
                  key={a.id}
                  message={
                    <div>
                      <Space>
                        <Badge status={a.is_read ? "default" : "processing"} />
                        <Text strong>{a.contact_name}</Text>
                        <Tag>{a.contact_rating}级</Tag>
                      </Space>
                    </div>
                  }
                  description={
                    <div>
                      <Text type="secondary" style={{ fontSize: 12 }}>{a.alert_reason}</Text>
                      {a.contact_phone && (
                        <div style={{ marginTop: 4 }}>
                          <PhoneOutlined /> {a.contact_phone}
                        </div>
                      )}
                    </div>
                  }
                  type="info"
                  style={{ marginBottom: 8 }}
                  action={
                    !a.is_read && (
                      <Button size="small" onClick={() => handleMarkRead(a.id)}>
                        标记已读
                      </Button>
                    )
                  }
                />
              ))
            )}
          </Card>

          {/* 历史中标参考 */}
          {data.history_reference && data.history_reference.length > 0 && (
            <Card title="📜 历史中标参考" size="small">
              {data.history_reference.slice(0, 5).map((h, idx) => (
                <div key={idx} style={{
                  padding: "6px 0", borderBottom: idx < data.history_reference.length - 1 ? "1px solid #f0f0f0" : "none",
                }}>
                  <Text strong>{h.winner_name}</Text>
                  <Tag style={{ marginLeft: 8 }}>{h.winner_type}</Tag>
                  <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>
                    {h.project_name} · 中标 {h.bid_amount}万 · {h.bid_open_date}
                  </div>
                </div>
              ))}
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
}

const BellOutlined = ({ children }) => <span>🔔{children}</span>;

export default AnnouncementDetail;
