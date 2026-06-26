import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Card, Table, Tag, Progress, Button, Space, Input, Select,
  Row, Col, Typography, Badge, Tooltip, message, Spin, Empty,
  Slider, DatePicker,
} from "antd";
import {
  ReloadOutlined, SearchOutlined, FilterOutlined,
  UserOutlined, CrownOutlined, ClockCircleOutlined,
  ThunderboltOutlined, ClearOutlined,
} from "@ant-design/icons";
import { getOpportunityList, fetchNewAnnouncements } from "../services/api";

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// ============================================================
// 常量
// ============================================================

const CATEGORY_OPTIONS = [
  { value: "", label: "全部类别" },
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
  { value: "", label: "全部" },
  { value: "低", label: "低陪跑概率" },
  { value: "中", label: "中陪跑概率" },
  { value: "高", label: "高陪跑概率" },
];

const PROBABILITY_COLORS = {
  "低": "green",
  "中": "orange",
  "高": "red",
};

// ============================================================
// 辅助函数
// ============================================================

function calcDaysLeft(deadline) {
  if (!deadline) return null;
  const now = new Date();
  const dl = new Date(deadline);
  const diff = Math.ceil((dl - now) / (1000 * 60 * 60 * 24));
  return diff;
}

function renderDaysLeft(deadline) {
  const days = calcDaysLeft(deadline);
  if (days === null) return <Text type="secondary">—</Text>;
  if (days < 0) {
    return <Tag color="default">已截止</Tag>;
  }
  if (days === 0) {
    return <Tag color="red">今日截止</Tag>;
  }
  if (days <= 3) {
    return <Tag color="red">剩余{days}天</Tag>;
  }
  if (days <= 7) {
    return <Tag color="orange">剩余{days}天</Tag>;
  }
  return <Text>{days} 天</Text>;
}

// Mock 数据（后端未就绪时使用）
function generateMockData() {
  const items = [];
  const purchasers = ["省公司", "广州分公司", "东莞分公司", "深圳分公司", "佛山分公司"];
  const categories = ["品牌策略类", "创意设计类", "媒介投放类", "活动执行类", "内容制作类", "新媒体运营类"];
  const methods = ["公开招标", "公开询比", "竞争性谈判", "单一来源"];
  const names = [
    "品牌策略规划服务", "广告创意设计项目", "信息流广告投放代理",
    "校园路演推广活动", "宣传物料设计与制作", "微信公众号代运营",
    "品牌健康度调研", "VI视觉系统升级", "KOL达人资源采购",
    "新品发布会活动", "短视频内容制作", "视频号直播运营",
  ];

  for (let i = 0; i < 25; i++) {
    const score = Math.floor(Math.random() * 60) + 25;
    const prob = score >= 75 ? "低" : score >= 50 ? "中" : "高";
    const deadline = new Date();
    deadline.setDate(deadline.getDate() + Math.floor(Math.random() * 60) - 5);

    const hasContact = Math.random() > 0.5;
    const hasIncumbent = Math.random() > 0.65;

    items.push({
      id: i + 1,
      title: `广东移动${purchasers[i % 5]}${names[i % names.length]}`,
      purchaser: purchasers[i % 5],
      purchaser_level: purchasers[i % 5],
      project_category: categories[i % 6],
      procurement_method: methods[i % 4],
      budget: Math.floor(Math.random() * 800) + 50,
      deadline: deadline.toISOString(),
      total_score: score,
      probability_label: prob,
      contact_name: hasContact ? ["张三", "李四", "王五"][i % 3] : null,
      incumbent_name: hasIncumbent ? ["省广集团", "蓝色光标", "因赛集团"][i % 3] : null,
    });
  }
  items.sort((a, b) => b.total_score - a.total_score);
  return items;
}

// ============================================================
// 主组件
// ============================================================

function OpportunityList() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [searchText, setSearchText] = useState("");

  // 筛选状态
  const [filterLevel, setFilterLevel] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterMethod, setFilterMethod] = useState("");
  const [filterProbability, setFilterProbability] = useState("");
  const [budgetRange, setBudgetRange] = useState([0, 1000]);

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
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
      Object.keys(params).forEach(k => params[k] === undefined && delete params[k]);

      const result = await getOpportunityList(params);
      if (result && result.items) {
        setData(result.items);
      } else if (Array.isArray(result)) {
        setData(result);
      }
    } catch (err) {
      console.warn("后端API不可用，使用Mock数据");
      let mockData = generateMockData();
      // 前端筛选
      if (searchText) mockData = mockData.filter(i => i.title.includes(searchText));
      if (filterLevel) mockData = mockData.filter(i => i.purchaser_level === filterLevel);
      if (filterCategory) mockData = mockData.filter(i => i.project_category === filterCategory);
      if (filterMethod) mockData = mockData.filter(i => i.procurement_method === filterMethod);
      if (filterProbability) mockData = mockData.filter(i => i.probability_label === filterProbability);
      mockData = mockData.filter(i => i.budget >= budgetRange[0] && i.budget <= budgetRange[1]);
      setData(mockData);
    } finally {
      setLoading(false);
    }
  }, [filterLevel, filterCategory, filterMethod, filterProbability, budgetRange, searchText]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 手动刷新
  const handleRefresh = async () => {
    setFetching(true);
    try {
      await fetchNewAnnouncements();
      message.success("数据采集已触发，请稍后刷新查看");
    } catch {
      message.warning("后端采集接口不可用，已刷新Mock数据");
      setData(generateMockData());
    } finally {
      setFetching(false);
      setTimeout(() => loadData(), 2000);
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

  // 表格列定义
  const columns = useMemo(() => [
    {
      title: "项目名称",
      dataIndex: "title",
      key: "title",
      width: 340,
      ellipsis: true,
      render: (text, record) => (
        <Space direction="vertical" size={0}>
          <a
            style={{ fontWeight: 500 }}
            onClick={() => message.info(`详情页: ${record.id}`)}
          >
            {text}
          </a>
          <Space size={4} wrap>
            {record.contact_name && (
              <Tag icon={<UserOutlined />} color="blue" style={{ fontSize: 11 }}>
                联系人：{record.contact_name}
              </Tag>
            )}
            {record.incumbent_name && (
              <Tag icon={<CrownOutlined />} color="gold" style={{ fontSize: 11 }}>
                在位者：{record.incumbent_name}
              </Tag>
            )}
          </Space>
        </Space>
      ),
    },
    {
      title: "采购方",
      dataIndex: "purchaser",
      key: "purchaser",
      width: 110,
      render: (text) => {
        const isProvince = text?.includes("省公司");
        return (
          <Tag color={isProvince ? "purple" : "blue"}>
            {text?.replace("分公司", "")}
          </Tag>
        );
      },
    },
    {
      title: "类别",
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
      title: "采购方式",
      dataIndex: "procurement_method",
      key: "procurement_method",
      width: 100,
      render: (m) => <Text>{m}</Text>,
    },
    {
      title: "预算",
      dataIndex: "budget",
      key: "budget",
      width: 90,
      sorter: (a, b) => (a.budget || 0) - (b.budget || 0),
      render: (val) => val ? <Text strong>{val}万</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: <><ClockCircleOutlined /> 截止</>,
      dataIndex: "deadline",
      key: "deadline",
      width: 100,
      sorter: (a, b) => calcDaysLeft(a.deadline) - calcDaysLeft(b.deadline),
      render: (dl) => renderDaysLeft(dl),
    },
    {
      title: "推荐指数",
      dataIndex: "total_score",
      key: "total_score",
      width: 160,
      sorter: (a, b) => a.total_score - b.total_score,
      defaultSortOrder: "descend",
      render: (score) => (
        <Progress
          percent={score}
          size="small"
          strokeColor={
            score >= 75 ? "#52c41a" : score >= 50 ? "#faad14" : "#ff4d4f"
          }
          format={(p) => `${p}分`}
          style={{ minWidth: 120 }}
        />
      ),
    },
    {
      title: "陪跑概率",
      dataIndex: "probability_label",
      key: "probability_label",
      width: 90,
      render: (label) => (
        <Badge
          status={label === "低" ? "success" : label === "中" ? "warning" : "error"}
          text={
            <Text strong style={{ color: PROBABILITY_COLORS[label] }}>
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
              loading={fetching}
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
              scroll={{ x: 1200 }}
              size="middle"
              locale={{ emptyText: "暂无数据" }}
            />
          )}
        </Spin>
      </Card>
    </div>
  );
}

export default OpportunityList;
