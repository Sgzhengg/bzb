import React, { useState, useMemo } from "react";
import {
  Card, Table, Tag, Progress, Button, Space, Input, Select,
  Row, Col, Typography, Badge, Tooltip, message, Spin, Empty,
  Slider,
} from "antd";
import {
  ReloadOutlined, SearchOutlined,
  ThunderboltOutlined, ClearOutlined, LinkOutlined,
  StarOutlined, StarFilled,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useOpportunityList, useFetchAnnouncements, useToggleFavorite } from "../services/apiHooks";

const { Title, Text } = Typography;

// ============================================================
// 常量
// ============================================================

const CATEGORY_OPTIONS = [
  { value: "", label: "全部种类" },
  { value: "品牌策略类", label: "品牌策略" },
  { value: "创意设计类", label: "创意设计" },
  { value: "媒介投放类", label: "媒介投放" },
  { value: "活动执行类", label: "活动执行" },
  { value: "内容制作类", label: "内容制作" },
  { value: "新媒体运营类", label: "新媒体运营" },
];

const METHOD_OPTIONS = [
  { value: "", label: "全部方式" },
  { value: "公开招标", label: "公开招标" },
  { value: "公开询比", label: "公开询比" },
  { value: "竞争性谈判", label: "竞争性谈判" },
  { value: "单一来源", label: "单一来源" },
];

const LEVEL_OPTIONS = [
  { value: "", label: "全部层级" },
  { value: "省公司", label: "省公司" },
  { value: "广州分公司", label: "广州分公司" },
  { value: "深圳分公司", label: "深圳分公司" },
  { value: "东莞分公司", label: "东莞分公司" },
  { value: "佛山分公司", label: "佛山分公司" },
];

const PROBABILITY_OPTIONS = [
  { value: "", label: "全部陪跑概率" },
  { value: "低", label: "低陪跑概率" },
  { value: "中", label: "中陪跑概率" },
  { value: "高", label: "高陪跑概率" },
];

// ============================================================
// 辅助函数
// ============================================================

function formatDate(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// ============================================================
// 主组件
// ============================================================

function OpportunityList() {
  const navigate = useNavigate();
  const [searchText, setSearchText] = useState("");

  // 筛选状态
  const [filterLevel, setFilterLevel] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterMethod, setFilterMethod] = useState("");
  const [filterProbability, setFilterProbability] = useState("");
  const [budgetRange, setBudgetRange] = useState([0, 1000]);

  // 构建查询参数
  const params = useMemo(() => {
    const result = {
      sort: "score_desc",
      purchaser_level: filterLevel || undefined,
      project_category: filterCategory || undefined,
      procurement_method: filterMethod || undefined,
      probability_label: filterProbability || undefined,
      budget_min: budgetRange[0] || undefined,
      budget_max: budgetRange[1] || undefined,
      search: searchText || undefined,
    };
    // 清除 undefined 值
    Object.keys(result).forEach(k => result[k] === undefined && delete result[k]);
    return result;
  }, [filterLevel, filterCategory, filterMethod, filterProbability, budgetRange, searchText]);

  // 使用 React Query hooks
  const { data: response, isLoading, refetch } = useOpportunityList(params);
  const fetchMutation = useFetchAnnouncements();
  const toggleFavoriteMutation = useToggleFavorite();

  const data = response?.items || [];

  // 手动刷新
  const handleRefresh = async () => {
    try {
      await fetchMutation.mutateAsync();
      message.success("数据采集已触发，请稍后刷新查看");
      setTimeout(() => refetch(), 2000);
    } catch {
      message.error("数据采集失败，请检查后端服务");
    }
  };

  const handleReset = () => {
    setFilterLevel("");
    setFilterCategory("");
    setFilterMethod("");
    setFilterProbability("");
    setBudgetRange([0, 1000]);
    setSearchText("");
  };

  // 表格列定义 — 对齐「致合项目查询汇总」Excel 模板
  const columns = useMemo(() => [
    {
      title: "招标单位",
      dataIndex: "industry",
      key: "industry",
      width: 220,
      ellipsis: true,
      render: (val) => val ? <Text>{val}</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: "省份",
      dataIndex: "province",
      key: "province",
      width: 70,
      render: (val) => val || <Text type="secondary">—</Text>,
    },
    {
      title: "地市",
      dataIndex: "city",
      key: "city",
      width: 80,
      render: (val) => val || <Text type="secondary">—</Text>,
    },
    {
      title: "项目名称",
      dataIndex: "title",
      key: "title",
      width: 320,
      ellipsis: true,
      render: (text, record) => (
        <a
          style={{ fontWeight: 500 }}
          onClick={() => navigate(`/opportunities/${record.id}`)}
        >
          {text}
        </a>
      ),
    },
    {
      title: "种类",
      dataIndex: "project_category",
      key: "project_category",
      width: 100,
      render: (cat) => {
        const colorMap = {
          "品牌策略类": "magenta", "创意设计类": "purple",
          "媒介投放类": "cyan", "活动执行类": "orange",
          "内容制作类": "geekblue", "新媒体运营类": "green",
        };
        return <Tag color={colorMap[cat] || "default"}>{cat?.replace("类", "")}</Tag>;
      },
    },
    {
      title: "预算金额\n（万元）",
      dataIndex: "budget",
      key: "budget",
      width: 110,
      sorter: (a, b) => (a.budget || 0) - (b.budget || 0),
      render: (val) => val ? <Text strong>{val} 万</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: "网址",
      dataIndex: "source_url",
      key: "source_url",
      width: 80,
      render: (url) => url && url.startsWith("http") ? (
        <a href={url} target="_blank" rel="noopener noreferrer">
          <LinkOutlined /> 查看
        </a>
      ) : <Text type="secondary">—</Text>,
    },
    {
      title: "报名截止日期",
      dataIndex: "deadline",
      key: "deadline",
      width: 115,
      sorter: (a, b) => new Date(a.deadline) - new Date(b.deadline),
      render: (val) => <Text>{formatDate(val)}</Text>,
    },
    {
      title: "投标日期",
      dataIndex: "bid_date",
      key: "bid_date",
      width: 105,
      render: (val) => val ? <Text>{formatDate(val)}</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: "报名费",
      dataIndex: "registration_fee",
      key: "registration_fee",
      width: 85,
      render: (val) => val ? <Text>¥{val}</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: "保证金",
      dataIndex: "deposit",
      key: "deposit",
      width: 90,
      render: (val) => val ? <Text>¥{val.toLocaleString()}</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: "推荐指数",
      dataIndex: "total_score",
      key: "total_score",
      width: 150,
      sorter: (a, b) => a.total_score - b.total_score,
      defaultSortOrder: "descend",
      render: (score) => (
        <Progress
          percent={score}
          size="small"
          strokeColor={score >= 75 ? "#52c41a" : score >= 50 ? "#faad14" : "#ff4d4f"}
          format={(p) => `${p}分`}
          style={{ minWidth: 110 }}
        />
      ),
    },
    {
      title: "陪跑概率",
      dataIndex: "probability_label",
      key: "probability_label",
      width: 95,
      render: (label) => (
        <Badge
          status={label === "低" ? "success" : label === "中" ? "warning" : "error"}
          text={
            <Text strong style={{ color: { "低": "green", "中": "orange", "高": "red" }[label] }}>
              {label === "低" ? "🟢 低" : label === "中" ? "🟡 中" : "🔴 高"}
            </Text>
          }
        />
      ),
    },
  ], []);

  return (
    <div>
      {/* 标题栏 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <ThunderboltOutlined /> 机会列表
          </Title>
        </Col>
        <Col>
          <Space>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              loading={fetchMutation.isLoading}
              onClick={handleRefresh}
            >
              刷新采集
            </Button>
            <Button icon={<ClearOutlined />} onClick={handleReset}>
              重置筛选
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 筛选栏 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col xs={24} sm={12} md={6}>
            <Input
              prefix={<SearchOutlined />}
              placeholder="搜索项目名称..."
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              value={filterLevel}
              onChange={setFilterLevel}
              options={LEVEL_OPTIONS}
              style={{ width: "100%" }}
              placeholder="采购方层级"
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              value={filterCategory}
              onChange={setFilterCategory}
              options={CATEGORY_OPTIONS}
              style={{ width: "100%" }}
              placeholder="项目类别"
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              value={filterMethod}
              onChange={setFilterMethod}
              options={METHOD_OPTIONS}
              style={{ width: "100%" }}
              placeholder="采购方式"
            />
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Select
              value={filterProbability}
              onChange={setFilterProbability}
              options={PROBABILITY_OPTIONS}
              style={{ width: "100%" }}
              placeholder="陪跑概率"
            />
          </Col>
          <Col xs={24} sm={12} md={3}>
            <Tooltip title={`预算: ${budgetRange[0]}万 - ${budgetRange[1]}万`}>
              <Slider
                range
                min={0}
                max={1000}
                step={50}
                value={budgetRange}
                onChange={setBudgetRange}
                marks={{ 0: "0", 500: "500万", 1000: "1000万" }}
              />
            </Tooltip>
          </Col>
        </Row>
      </Card>

      {/* 数据表格 */}
      <Card>
        <Spin spinning={loading}>
          {data.length === 0 && !loading ? (
            <Empty description="暂无匹配的招标公告" />
          ) : (
            <Table
              columns={columns}
              dataSource={data}
              rowKey="id"
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条`,
              }}
              scroll={{ x: 1800 }}
              size="small"
              locale={{ emptyText: "暂无数据" }}
            />
          )}
        </Spin>
      </Card>
    </div>
  );
}

export default OpportunityList;
