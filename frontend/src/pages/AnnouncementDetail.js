import React, { useState, useEffect, useCallback } from "react";
import {
  Card, Descriptions, Tag, Typography, Spin, Empty, Button, Space, message, Tooltip,
} from "antd";
import {
  ArrowLeftOutlined, StarOutlined, StarFilled, LinkOutlined, ClockCircleOutlined,
} from "@ant-design/icons";
import { useParams, useNavigate } from "react-router-dom";
import { getAnnouncementDetail, toggleFavorite } from "../services/api";
const { Title, Text, Paragraph } = Typography;

const PROCUREMENT_COLORS = {
  "公开招标": "blue", "公开询比": "green",
  "竞争性谈判": "orange", "单一来源": "red",
};

function AnnouncementDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
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

  useEffect(() => { loadDetail(); }, [loadDetail]);

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
  if (!data) return <Empty description="公告不存在" />;

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

      {/* 标题 */}
      <Card style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>{data.title}</Title>
        <Space wrap size={[8, 8]} style={{ marginTop: 12 }}>
          <Tag color="blue">{data.purchaser}</Tag>
          <Tag color={PROCUREMENT_COLORS[data.procurement_method]}>
            {data.procurement_method}
          </Tag>
          <Tag color="purple">{data.project_category}</Tag>
          {data.source_url && (
            <Tag icon={<LinkOutlined />} color="geekblue" style={{ cursor: 'pointer' }}
              onClick={() => window.open(data.source_url, '_blank')}>
              原文链接
            </Tag>
          )}
        </Space>
      </Card>

      {/* 基本信息 */}
      <Card title="📋 基本信息">
        <Descriptions column={{ xs: 1, sm: 2 }} size="small" bordered>
          <Descriptions.Item label="省份">{data.province || "—"}</Descriptions.Item>
          <Descriptions.Item label="城市">{data.city || "—"}</Descriptions.Item>
          <Descriptions.Item label="采购方">{data.purchaser || data.industry || "—"}</Descriptions.Item>
          <Descriptions.Item label="层级">{data.purchaser_level || "—"}</Descriptions.Item>
          <Descriptions.Item label="项目类别">{data.project_category}</Descriptions.Item>
          <Descriptions.Item label="采购方式">
            <Tag color={PROCUREMENT_COLORS[data.procurement_method]}>{data.procurement_method}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="公告日期">{data.announce_date || "—"}</Descriptions.Item>
          <Descriptions.Item label="关键截止日期">
            <ClockCircleOutlined style={{ marginRight: 4 }} />
            {data.deadline && !data.deadline.startsWith("1900") ? data.deadline : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="投标日期">
            {data.bid_date && !data.bid_date.startsWith("1900") ? data.bid_date : "—"}
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
          <Descriptions.Item label="资格要求" span={2}>
            <Paragraph ellipsis={{ rows: 3, expandable: true }}>
              {data.qualification_requirements || "—"}
            </Paragraph>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}

export default AnnouncementDetail;
