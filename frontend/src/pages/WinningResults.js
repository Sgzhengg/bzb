import React, { useState, useEffect, useCallback } from "react";
import {
  Card, Table, Tag, Typography, Row, Col, Statistic,
  Input, Select, Button, Space, Spin, Empty, message, Popconfirm,
} from "antd";
import {
  TrophyOutlined, SearchOutlined, DollarOutlined,
  ReloadOutlined, LinkOutlined, DeleteOutlined,
} from "@ant-design/icons";
import apiClient from "../services/api";

const { Title, Text } = Typography;

const WINNER_COLORS = {
  "头部常客": "red", "中小公司": "green", "新进入者": "blue",
};

function WinningResults() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [total, setTotal] = useState(0);
  const [searchText, setSearchText] = useState("");
  const [filterType, setFilterType] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (searchText) params.search = searchText;
      if (filterType) params.winner_type = filterType;
      const result = await apiClient.get("/awards", { params });
      setData(result.items || []);
      setTotal(result.total || 0);
    } catch {
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [searchText, filterType]);

  const loadStats = useCallback(async () => {
    try {
      const result = await apiClient.get("/awards/stats");
      setStats(result);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { loadData(); loadStats(); }, [loadData, loadStats]);

  const handleDelete = async (id, projectName) => {
    try {
      await apiClient.delete(`/awards/${id}`);
      message.success(`已删除: ${projectName}`);
      loadData();
      loadStats();
    } catch {
      message.error("删除失败，请重试");
    }
  };

  const columns = [
    {
      title: "项目名称", dataIndex: "project_name", key: "project_name",
      width: 300, ellipsis: true,
    },
    {
      title: "中标方", dataIndex: "winner_name", key: "winner", width: 160,
      render: (v) => <Text strong>{v}</Text>,
    },
    {
      title: "中标方类型", dataIndex: "winner_type", key: "type", width: 100,
      render: (v) => <Tag color={WINNER_COLORS[v] || "default"}>{v}</Tag>,
    },
    {
      title: "中标金额/份额", dataIndex: "discount_rate", key: "amount_share", width: 120,
      render: (v) => v ? <Text strong style={{ color: "#1677ff" }}>{v}%</Text> : "—",
    },
    {
      title: "项目类别", dataIndex: "project_category", key: "category", width: 110,
      render: (v) => <Tag color="purple">{v}</Tag>,
    },
    {
      title: "公示日期", dataIndex: "bid_open_date", key: "date", width: 110,
      render: (v) => v || <Text type="secondary">—</Text>,
    },
    {
      title: "公告链接", dataIndex: "source_url", key: "url", width: 80,
      render: (url) => url ? (
        <a href={url} target="_blank" rel="noopener noreferrer">
          <LinkOutlined /> 查看
        </a>
      ) : <Text type="secondary">—</Text>,
    },
    {
      title: "操作", key: "action", width: 60, fixed: "right",
      render: (_, record) => (
        <Popconfirm
          title="确定删除？"
          description={`将删除「${record.project_name?.slice(0, 20)}...」的中标记录`}
          onConfirm={() => handleDelete(record.id, record.project_name)}
          okText="删除"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <Button type="link" danger size="small" icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Title level={3}><TrophyOutlined /> 中标结果</Title>

      {/* 统计卡片 */}
      {stats && (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={6}>
            <Card>
              <Statistic title="中标总数" value={stats.total} prefix={<TrophyOutlined />}
                valueStyle={{ color: "#1677ff" }} suffix="条" />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card>
              <Statistic title="中标总金额" value={stats.total_amount}
                prefix={<DollarOutlined />} valueStyle={{ color: "#52c41a" }}
                suffix="万元" />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card>
              <Statistic title="头部常客"
                value={stats.winner_types?.find(t => t.type === "头部常客")?.count || 0}
                valueStyle={{ color: "#ff4d4f" }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card>
              <Statistic title="中小公司/新进入者"
                value={(stats.winner_types?.find(t => t.type === "中小公司")?.count || 0) +
                       (stats.winner_types?.find(t => t.type === "新进入者")?.count || 0)}
                valueStyle={{ color: "#722ed1" }} />
            </Card>
          </Col>
        </Row>
      )}

      {/* 筛选栏 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col xs={24} sm={12} md={6}>
            <Input prefix={<SearchOutlined />} placeholder="搜索项目/中标方..."
              value={searchText} onChange={e => setSearchText(e.target.value)} allowClear />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select value={filterType} onChange={setFilterType}
              placeholder="中标方类型" allowClear style={{ width: "100%" }}
              options={[
                { value: "", label: "全部类型" },
                { value: "头部常客", label: "头部常客" },
                { value: "中小公司", label: "中小公司" },
                { value: "新进入者", label: "新进入者" },
              ]} />
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
          </Col>
        </Row>
      </Card>

      {/* 数据表格 */}
      <Card>
        <Spin spinning={loading}>
          {data.length === 0 && !loading ? (
            <Empty description="暂无中标结果数据。请先运行爬虫采集数据。" />
          ) : (
            <Table columns={columns} dataSource={data} rowKey="id"
              pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
              scroll={{ x: 1500 }} size="small" />
          )}
        </Spin>
      </Card>
    </div>
  );
}

export default WinningResults;
