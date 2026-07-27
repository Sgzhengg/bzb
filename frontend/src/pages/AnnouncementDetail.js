import React, { useState, useEffect, useCallback } from "react";
import {
  Card, Descriptions, Tag, Typography, Spin, Empty, Button, Space, App, Tooltip,
  Divider, List, Alert, Row, Col, Progress,
} from "antd";
import {
  ArrowLeftOutlined, StarOutlined, StarFilled, LinkOutlined, ClockCircleOutlined,
  RobotOutlined, ThunderboltOutlined, WarningOutlined, SafetyCertificateOutlined,
  RiseOutlined, CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined,
  PushpinOutlined,
} from "@ant-design/icons";
import { useParams, useNavigate } from "react-router-dom";
import { getAnnouncementDetail, toggleFavorite, getAISummary } from "../services/api";
const { Title, Text, Paragraph } = Typography;

const PROCUREMENT_COLORS = {
  "公开招标": "blue", "公开询比": "green",
  "竞争性谈判": "orange", "单一来源": "red",
};

function AnnouncementDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isFav, setIsFav] = useState(false);
  const [notFound, setNotFound] = useState(false);

  // AI 摘要状态
  const [aiSummary, setAiSummary] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiStatus, setAiStatus] = useState(null);

  const loadDetail = useCallback(async () => {
    setLoading(true);
    setNotFound(false);
    try {
      const result = await getAnnouncementDetail(id);
      setData(result);
      setIsFav(result.is_favorited || false);
    } catch (err) {
      if (err.response && err.response.status === 404) {
        setNotFound(true);
      } else {
        message.error("加载公告详情失败");
      }
    } finally {
      setLoading(false);
    }
  }, [id, message]);

  useEffect(() => { loadDetail(); }, [loadDetail]);

  const handleAISummary = async () => {
    setAiLoading(true);
    try {
      const result = await getAISummary(id);
      setAiStatus(result.status);
      if (result.summary) setAiSummary(result.summary);
      if (result.status === "no_content") message.info(result.message || "公告正文为空");
      else if (result.status === "llm_unavailable") message.warning("LLM 未配置");
      else if (result.status === "generated") message.success("AI 智能分析已生成");
    } catch (e) {
      message.error("AI 分析请求失败");
    } finally {
      setAiLoading(false);
    }
  };

  useEffect(() => {
    if (data && data.ai_summary) setAiSummary(data.ai_summary);
  }, [data]);

  const handleFavorite = async () => {
    try {
      const result = await toggleFavorite(id);
      setIsFav(result.is_favorited);
      message.success(result.message);
    } catch {
      message.error("操作失败");
    }
  };

  if (loading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (!data) {
    return (
      <Empty description={notFound ? `公告 #${id} 不存在` : "公告不存在"}>
        <Button type="primary" onClick={() => navigate("/opportunities")}>返回列表</Button>
      </Empty>
    );
  }

  return (
    <div>
      {/* 返回 + 操作栏 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/opportunities")}>返回列表</Button>
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

      {/* 标题 */}
      <Card style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>{data.title}</Title>
        <Space wrap size={[8, 8]} style={{ marginTop: 12 }}>
          {data.purchaser && <Tag color="blue">{data.purchaser}</Tag>}
          {data.procurement_method && <Tag color={PROCUREMENT_COLORS[data.procurement_method] || "default"}>{data.procurement_method}</Tag>}
          {data.project_category && <Tag color="purple">{data.project_category}</Tag>}
          {data.province && <Tag color="cyan">{data.province}</Tag>}
          {data.city && <Tag>{data.city}</Tag>}
          {data.budget != null && <Tag color="gold" style={{ fontWeight: 600 }}>💰 {data.budget} 万元</Tag>}
          {data.source_url && (
            <Tag icon={<LinkOutlined />} color="geekblue" style={{ cursor: 'pointer' }}
              onClick={() => window.open(data.source_url, '_blank')}>原文链接</Tag>
          )}
        </Space>
      </Card>

      <Row gutter={16}>
        {/* 左侧：基本信息 */}
        <Col xs={24} lg={14}>
          <Card title="📋 基本信息" style={{ marginBottom: 16 }}>
            <Descriptions column={{ xs: 1, sm: 2 }} size="small" bordered>
              <Descriptions.Item label="省份">{data.province || "—"}</Descriptions.Item>
              <Descriptions.Item label="城市">{data.city || "—"}</Descriptions.Item>
              <Descriptions.Item label="采购方">{data.purchaser || data.industry || "—"}</Descriptions.Item>
              <Descriptions.Item label="层级">{data.purchaser_level || "—"}</Descriptions.Item>
              <Descriptions.Item label="项目类别">{data.project_category || "—"}</Descriptions.Item>
              <Descriptions.Item label="采购方式"><Tag color={PROCUREMENT_COLORS[data.procurement_method]}>{data.procurement_method}</Tag></Descriptions.Item>
              <Descriptions.Item label="公告日期">{data.announce_date || "—"}</Descriptions.Item>
              <Descriptions.Item label="报名截止">
                <span><ClockCircleOutlined style={{ marginRight: 4 }} />
                {data.deadline && !data.deadline.startsWith("1900") ? data.deadline : "—"}
                {data.deadline_time ? ` ${data.deadline_time}` : ""}</span>
              </Descriptions.Item>
              <Descriptions.Item label="投标日期">
                {data.bid_date && !data.bid_date.startsWith("1900") ? data.bid_date : "—"}
                {data.bid_time ? ` ${data.bid_time}` : ""}
              </Descriptions.Item>
              <Descriptions.Item label="预算金额">
                <Text strong style={{ fontSize: 16, color: "#1677ff" }}>
                  {data.budget != null ? `${data.budget} 万元` : "—"}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="报名费">
                {data.registration_fee != null && data.registration_fee > 0 ? `${data.registration_fee} 元` : "—"}
              </Descriptions.Item>
              <Descriptions.Item label="保证金">
                {data.deposit != null && data.deposit > 0 ? `${data.deposit} 元` : "—"}
              </Descriptions.Item>
              <Descriptions.Item label="数据来源">
                {data.data_source ? <Tag>{data.data_source}</Tag> : "—"}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {/* 原文内容 */}
          {(data.original_content || data.original_content_html) && (
            <Card title="📄 公告原文" style={{ marginBottom: 16 }}>
              {data.original_content_html ? (
                <div dangerouslySetInnerHTML={{ __html: data.original_content_html }}
                  style={{ maxHeight: 400, overflow: "auto", fontSize: 13, lineHeight: 1.6 }} />
              ) : (
                <Paragraph ellipsis={{ rows: 8, expandable: true, symbol: "展开全文" }}
                  style={{ whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.6 }}>
                  {data.original_content || "（暂无原文）"}
                </Paragraph>
              )}
            </Card>
          )}
        </Col>

        {/* 右侧：AI 智能分析 */}
        <Col xs={24} lg={10}>
          <Card
            title={<><RobotOutlined /> AI 智能分析</>}
            style={{ marginBottom: 16 }}
            extra={aiStatus === "cached" ? (
              <Button size="small" icon={<ReloadOutlined />} loading={aiLoading} onClick={handleAISummary}>重新生成</Button>
            ) : null}
          >
            {!aiSummary ? (
              <div style={{ textAlign: "center", padding: "20px 0" }}>
                {aiStatus === "no_content" ? (
                  <Empty description="正文为空，无法分析" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                ) : aiStatus === "llm_unavailable" ? (
                  <Empty description="LLM 未配置" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                ) : (
                  <>
                    <RobotOutlined style={{ fontSize: 36, color: "#1677ff", marginBottom: 12 }} />
                    <Paragraph type="secondary">点击下方按钮，AI 将自动分析公告内容。</Paragraph>
                    <Button type="primary" icon={<ThunderboltOutlined />}
                      loading={aiLoading} size="large" onClick={handleAISummary}>
                      {aiLoading ? "分析中..." : "🤖 开始 AI 分析"}
                    </Button>
                  </>
                )}
              </div>
            ) : (
              <AISummaryPanel summary={aiSummary} />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}

// ============================================================
// AI 摘要展示子组件（不含资金健康度/采购公平性/综合风险）
// ============================================================
function AISummaryPanel({ summary }) {
  if (!summary) return null;

  return (
    <div>
      {/* 一句话摘要 */}
      {summary.one_liner && (
        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ fontSize: 13 }}>📌 一句话摘要</Text>
          <Paragraph style={{ margin: "4px 0 0", fontSize: 13, lineHeight: 1.6, color: "#333" }}>
            {summary.one_liner}
          </Paragraph>
        </div>
      )}

      {/* 项目简报 */}
      {summary.brief && (
        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ fontSize: 13 }}>📋 项目简报</Text>
          <Paragraph style={{ margin: "4px 0 0", fontSize: 13, lineHeight: 1.6, color: "#333" }}>
            {summary.brief}
          </Paragraph>
        </div>
      )}

      <Divider style={{ margin: "10px 0" }} />

      {/* 资格要求 */}
      {summary.qualifications && summary.qualifications.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ fontSize: 13 }}><SafetyCertificateOutlined /> 资格要求</Text>
          <List size="small" dataSource={summary.qualifications}
            renderItem={item => (
              <List.Item style={{ padding: "4px 0" }}>
                <Space align="start">
                  {item.is_hard_gate ? (
                    <PushpinOutlined style={{ color: "#fa8c16", marginTop: 3 }} />
                  ) : (
                    <CheckCircleOutlined style={{ color: "#52c41a", marginTop: 3 }} />
                  )}
                  <div>
                    <Text style={{ fontSize: 12 }}>{item.requirement}</Text>
                    <br />
                    <Tag color={item.is_hard_gate ? "red" : "green"} style={{ fontSize: 11, marginTop: 2 }}>
                      {item.is_hard_gate ? "硬性门槛" : "软性要求"}
                    </Tag>
                    {item.our_advantage && (
                      <Text type="secondary" style={{ fontSize: 11, marginLeft: 4 }}>{item.our_advantage}</Text>
                    )}
                  </div>
                </Space>
              </List.Item>
            )}
          />
        </div>
      )}

      {/* 硬性门槛摘要 */}
      {summary.hard_gates && summary.hard_gates.length > 0 && (
        <Alert style={{ marginBottom: 12 }}
          message={<span><WarningOutlined /> 硬性门槛：{summary.hard_gates.join("；")}</span>}
          type="warning" showIcon />
      )}

      {/* 风险提示 */}
      {summary.risks && summary.risks.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ fontSize: 13 }}><WarningOutlined style={{ color: "#faad14" }} /> 风险提示</Text>
          <List size="small" dataSource={summary.risks}
            renderItem={item => (
              <List.Item style={{ padding: "4px 0" }}>
                <Space align="start">
                  <Tag color={item.severity === "高" ? "red" : item.severity === "中" ? "orange" : "green"}
                    style={{ minWidth: 30, textAlign: "center" }}>{item.severity}</Tag>
                  <div>
                    <Text style={{ fontSize: 12 }}>
                      <Tag color="geekblue" style={{ fontSize: 10 }}>{item.risk_type}</Tag>
                      {item.description}
                    </Text>
                  </div>
                </Space>
              </List.Item>
            )}
          />
        </div>
      )}

      {/* 投标建议 */}
      <Divider style={{ margin: "10px 0" }} />
      <div style={{ textAlign: "center", marginBottom: 8 }}>
        <Tag
          icon={summary.should_bid ? <RiseOutlined /> : <CloseCircleOutlined />}
          color={summary.should_bid ? "success" : "error"}
          style={{ padding: "4px 12px", fontSize: 14 }}
        >
          {summary.should_bid ? "✅ 建议参与投标" : "❌ 不建议参与"}
        </Tag>
      </div>

      {/* 策略建议 */}
      {summary.strategy && summary.strategy.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <Text strong style={{ fontSize: 13 }}><RiseOutlined /> 策略建议</Text>
          <List size="small"
            dataSource={[...summary.strategy].sort((a, b) => (a.priority || 3) - (b.priority || 3))}
            renderItem={(item, idx) => (
              <List.Item style={{ padding: "4px 0" }}>
                <Space align="start">
                  <Tag color={item.priority === 1 ? "red" : item.priority === 2 ? "orange" : "blue"}>
                    P{item.priority || 3}
                  </Tag>
                  <Text style={{ fontSize: 12 }}>{item.advice}</Text>
                </Space>
              </List.Item>
            )}
          />
        </div>
      )}
    </div>
  );
}

export default AnnouncementDetail;
