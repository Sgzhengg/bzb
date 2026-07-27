import React, { useState, useMemo, useEffect, useRef } from "react";
import {
  Card, Table, Tag, Button, Space, Input, Select, Progress,
  Row, Col, Typography, Tooltip, App, Spin, Empty,
  Slider, Modal, Descriptions, Divider, Steps, DatePicker,
} from "antd";
import {
  SearchOutlined,
  ThunderboltOutlined,
  StarOutlined, StarFilled,
  ArrowLeftOutlined,
  CloudDownloadOutlined,
  DownloadOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LinkOutlined,
  RobotOutlined,
  CalendarOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useOpportunityList } from "../services/apiHooks";

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

const NOTICE_TYPE_OPTIONS = [
  { value: "", label: "全部公告" },
  { value: "opinion", label: "征集意见公告" },
  { value: "bidding", label: "招标公告" },
];

// V3 新增：数据来源选项
const DATA_SOURCE_OPTIONS = [
  { value: "", label: "全部来源" },
  { value: "b2b_10086", label: "中国移动" },
  { value: "telecom", label: "中国电信" },
  { value: "unicom", label: "中国联通" },
  { value: "gd_zbtb", label: "广东招标监管网" },
  { value: "gd_ygp", label: "广东公共资源平台" },
];

// V2 新增：省份选项（重点省份 + 全部）
const PROVINCE_OPTIONS = [
  { value: "", label: "全部省份" },
  { value: "广东", label: "广东" },
  { value: "广西", label: "广西" },
  { value: "福建", label: "福建" },
  { value: "海南", label: "海南" },
  { value: "浙江", label: "浙江" },
  { value: "湖南", label: "湖南" },
  { value: "安徽", label: "安徽" },
  { value: "山东", label: "山东" },
  { value: "江苏", label: "江苏" },
  { value: "四川", label: "四川" },
  { value: "湖北", label: "湖北" },
  { value: "河南", label: "河南" },
  { value: "北京", label: "北京" },
  { value: "上海", label: "上海" },
  { value: "重庆", label: "重庆" },
  { value: "天津", label: "天津" },
];

// 省份→城市 映射（用于联动筛选）
const PROVINCE_CITIES = {
  "广东": ["全部城市", "广州", "深圳", "东莞", "佛山", "珠海", "惠州", "中山", "江门", "汕头", "湛江", "茂名", "肇庆", "梅州", "汕尾", "河源", "阳江", "清远", "韶关", "潮州", "揭阳", "云浮"],
  "广西": ["全部城市", "南宁", "柳州", "桂林", "玉林", "梧州", "北海", "贵港", "钦州", "百色", "河池", "贺州", "来宾", "崇左", "防城港"],
  "福建": ["全部城市", "福州", "厦门", "泉州", "漳州", "龙岩", "三明", "南平", "莆田", "宁德"],
  "海南": ["全部城市", "海口", "三亚", "儋州"],
  "浙江": ["全部城市", "杭州", "宁波", "温州", "嘉兴", "湖州", "绍兴", "金华", "衢州", "舟山", "台州", "丽水"],
  "湖南": ["全部城市", "长沙", "株洲", "湘潭", "衡阳", "邵阳", "岳阳", "常德", "张家界", "益阳", "郴州", "永州", "怀化", "娄底"],
  "安徽": ["全部城市", "合肥", "芜湖", "蚌埠", "淮南", "马鞍山", "淮北", "铜陵", "安庆", "黄山", "滁州", "阜阳", "宿州", "六安", "亳州", "池州", "宣城"],
  "山东": ["全部城市", "济南", "青岛", "淄博", "枣庄", "东营", "烟台", "潍坊", "济宁", "泰安", "威海", "日照", "临沂", "德州", "聊城", "滨州", "菏泽"],
  "江苏": ["全部城市", "南京", "苏州", "无锡", "常州", "南通", "扬州", "镇江", "泰州", "盐城", "徐州", "淮安", "连云港", "宿迁"],
  "四川": ["全部城市", "成都", "绵阳", "德阳", "宜宾", "南充", "泸州", "达州", "乐山", "凉山", "内江", "自贡", "眉山", "广安", "遂宁", "攀枝花", "广元", "资阳", "巴中", "雅安"],
  "湖北": ["全部城市", "武汉", "宜昌", "襄阳", "荆州", "黄冈", "孝感", "十堰", "荆门", "黄石", "咸宁", "恩施", "鄂州", "随州"],
  "河南": ["全部城市", "郑州", "洛阳", "南阳", "许昌", "周口", "新乡", "商丘", "驻马店", "信阳", "平顶山", "开封", "安阳", "焦作", "濮阳", "漯河", "三门峡", "鹤壁"],
  "北京": ["全部城市", "东城", "西城", "朝阳", "海淀", "丰台", "石景山", "通州", "大兴", "顺义", "昌平", "房山"],
  "上海": ["全部城市", "浦东新区", "黄浦", "徐汇", "长宁", "静安", "普陀", "虹口", "杨浦", "闵行", "宝山", "嘉定", "松江"],
  "重庆": ["全部城市", "渝中", "江北", "南岸", "沙坪坝", "九龙坡", "大渡口", "北碚", "渝北", "巴南", "万州", "涪陵"],
  "天津": ["全部城市", "和平", "河东", "河西", "南开", "河北", "红桥", "滨海新区", "东丽", "西青", "津南", "北辰", "武清"],
};

// ============================================================
// 辅助函数
// ============================================================

function formatDate(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "—";
  // 1900-01-01 为数据库默认值，视为无数据
  if (d.getFullYear() < 2000) return "—";
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// ============================================================
// 主组件
// ============================================================

function OpportunityList() {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [searchText, setSearchText] = useState("");

  // 筛选状态
  const [filterProvince, setFilterProvince] = useState("");   // V2 新增
  const [filterCity, setFilterCity] = useState("");           // V2 新增
  const [filterCategory, setFilterCategory] = useState("");
  const [filterMethod, setFilterMethod] = useState("");
  const [filterNoticeType, setFilterNoticeType] = useState(""); // 公告类型筛选
  const [filterDataSource, setFilterDataSource] = useState("");   // V3: 数据来源筛选
  const [collectedFrom, setCollectedFrom] = useState(null);       // 采集时间起
  const [collectedTo, setCollectedTo] = useState(null);           // 采集时间止
  const [budgetRange, setBudgetRange] = useState([0, 1000]);
  const [showFavorites, setShowFavorites] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [provinceModalVisible, setProvinceModalVisible] = useState(false);
  const [exportModalVisible, setExportModalVisible] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // 采集弹窗状态
  const [selectedAdapter, setSelectedAdapter] = useState("b2b_10086");
  const [selectedProvinces, setSelectedProvinces] = useState([]);
  const [fetchDateRange, setFetchDateRange] = useState(null); // [dayjs, dayjs] 或 null
  const [fetchProgress, setFetchProgress] = useState(null); // {taskId, status, progress, message, ...}
  const pollingRef = useRef(null);

  // 停止轮询
  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  // 组件卸载时清理
  useEffect(() => () => stopPolling(), []);

  const startFetch = async (province, adapter = "", dateFrom = "", dateTo = "") => {
    setProvinceModalVisible(false);
    setFetching(true);
    try {
      const result = await fetchNewAnnouncements(province, adapter, dateFrom, dateTo);
      if (result.task_id) {
        // 开始轮询进度
        setFetchProgress({
          taskId: result.task_id,
          status: "starting",
          progress: 0,
          message: result.message || "正在启动...",
        });

        stopPolling();
        pollingRef.current = setInterval(async () => {
          try {
            const status = await getFetchStatus(result.task_id);
            setFetchProgress(prev => ({
              ...prev,
              ...status,
            }));

            if (status.status === "completed") {
              stopPolling();
              message.success(status.message || "采集完成！");
              setTimeout(() => {
                window._bzbCheckNew?.();
                setFetchProgress(null);
                setFetching(false);
                refetch();
              }, 2000);
            } else if (status.status === "failed") {
              stopPolling();
              message.error(status.message || "采集失败");
              setTimeout(() => {
                setFetchProgress(null);
                setFetching(false);
              }, 3000);
            }
          } catch (err) {
            // 404 表示任务已过期，停止轮询
            if (err?.response?.status === 404) {
              stopPolling();
              setFetchProgress(null);
              setFetching(false);
              message.warning("任务已过期，请重新采集");
            }
            // 其他错误静默继续
          }
        }, 1500);
      } else {
        message.success(result.message || "采集任务已启动");
        setFetching(false);
        setTimeout(() => refetch(), 5000);
        setTimeout(() => refetch(), 15000);
      }
    } catch {
      message.error("启动采集失败");
      setFetching(false);
    }
  };

  // 城市选项（根据选中省份联动）
  const cityOptions = useMemo(() => {
    if (!filterProvince) return [{ value: "", label: "请先选省份" }];
    const cities = PROVINCE_CITIES[filterProvince] || ["全部城市"];
    return cities.map(c => ({
      value: c === "全部城市" ? "" : c,
      label: c,
    }));
  }, [filterProvince]);

  // 省份切换时重置城市
  const handleProvinceChange = (val) => {
    setFilterProvince(val);
    setFilterCity("");
    setCurrentPage(1);
  };

  // 筛选变更时回到第1页
  useEffect(() => {
    setCurrentPage(1);
  }, [filterNoticeType, filterCategory, filterMethod, filterDataSource, searchText, collectedFrom, collectedTo]);

  // 构建查询参数
  const params = useMemo(() => {
    const result = {
      sort: "score_desc",
      province: filterProvince || undefined,           // V2 新增
      city: filterCity || undefined,                   // V2 新增
      project_category: filterCategory || undefined,
      procurement_method: filterMethod || undefined,
      data_source: filterDataSource || undefined,       // V3: 数据来源
      collected_from: collectedFrom ? collectedFrom.format("YYYY-MM-DD") : undefined,
      collected_to: collectedTo ? collectedTo.format("YYYY-MM-DD") : undefined,
      budget_min: budgetRange[0] || undefined,
      budget_max: budgetRange[1] || undefined,
      search: searchText || undefined,
      favorites_only: showFavorites || undefined,
      notice_type: filterNoticeType || undefined,
      page: currentPage,
      page_size: pageSize,
    };
    // 清除 undefined 值
    Object.keys(result).forEach(k => result[k] === undefined && delete result[k]);
    return result;
  }, [filterProvince, filterCity, filterCategory, filterMethod, filterNoticeType, filterDataSource, budgetRange, searchText, showFavorites, currentPage, pageSize, collectedFrom, collectedTo]);

  // 公告内容模态框状态
  const [contentModalVisible, setContentModalVisible] = useState(false);
  const [contentData, setContentData] = useState(null);

  // 使用 React Query hooks
  const { data: response, isLoading, refetch } = useOpportunityList(params);

  const data = response?.items || [];

  // 处理公告内容查看 - 优先直达详情页，否则显示模态框
  const handleViewOriginal = async (record) => {
    try {
      const result = await getAnnouncementOriginal(record.id);

      if (result.found) {
        if (result.detail_url) {
          // 有直达详情页 URL，直接在新标签页打开
          window.open(result.detail_url, '_blank');
          message.success("已在新标签页打开公告详情页");
        } else if (result.notice_content) {
          // 有公告内容但无详情 URL，在模态框中显示
          setContentData({
            title: result.title || record.title,
            publish_date: result.publish_date,
            publish_type: result.publish_type,
            company: result.company,
            deadline: result.deadline,
            bid_date: result.bid_date,
            notice_content: result.notice_content,
            source_url: result.search_url,
          });
          setContentModalVisible(true);
          message.success("已获取公告内容");
        } else {
          // 找到匹配但无详情，打开搜索页
          window.open(result.search_url, '_blank');
          message.info("已打开 b2b 搜索页");
        }
      } else {
        // 未找到，直接在新标签页打开 b2b 搜索
        const searchUrl = result.search_url || 'https://b2b.10086.cn/b2b/main/listVendorNotice.html?noticeType=2';
        window.open(searchUrl, '_blank');
        message.info("已在新标签页打开 b2b 搜索页");
      }
    } catch (error) {
      console.error("获取公告详情失败:", error);
      window.open('https://b2b.10086.cn/b2b/main/listVendorNotice.html?noticeType=2', '_blank');
      message.error("获取公告内容失败，已打开 b2b 网站");
    }
  };

  const handleContentModalClose = () => {
    setContentModalVisible(false);
    setContentData(null);
  };

  // 表格列定义
  const columns = useMemo(() => [
    {
      title: "来源",
      dataIndex: "data_source",
      key: "data_source",
      width: 90,
      render: (val) => {
        const sourceMap = {
          "b2b_10086": { label: "移动", color: "#1677ff" },
          "telecom": { label: "电信", color: "#52c41a" },
          "unicom": { label: "联通", color: "#fa541c" },
          "gd_zbtb": { label: "广东招标", color: "#722ed1" },
          "gd_ygp": { label: "广东资源", color: "#13c2c2" },
        };
        const info = sourceMap[val];
        return info ? <Tag color={info.color}>{info.label}</Tag> : (val ? <Tag>{val}</Tag> : <Text type="secondary">—</Text>);
      },
    },
    {
      title: "省份",
      dataIndex: "province",
      key: "province",
      width: 80,
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
      render: (val) => (val != null && val !== 0) ? <Text strong>{val} 万</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: "公告日期",
      dataIndex: "announce_date",
      key: "announce_date",
      width: 105,
      render: (val) => <Text>{formatDate(val)}</Text>,
    },
    {
      title: "网址",
      dataIndex: "source_url",
      key: "source_url",
      width: 100,
      render: (url, record) => (
        <Space size={0}>
          <a onClick={() => navigate(`/opportunities/${record.id}`)}>
            详情
          </a>
          <Divider type="vertical" />
          <a href={record.source_url} target="_blank" rel="noopener noreferrer" style={{ color: '#1677ff' }}>
            <LinkOutlined /> 原文
          </a>
        </Space>
      ),
    },
    {
      title: "报名/反馈截止日期",
      dataIndex: "deadline",
      key: "deadline",
      width: 130,
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
      render: (val) => val ? <Text>¥{val}</Text> : <Text>无</Text>,
    },
    {
      title: "保证金",
      dataIndex: "deposit",
      key: "deposit",
      width: 90,
      render: (val) => val ? <Text>¥{val.toLocaleString()}</Text> : <Text>无</Text>,
    },
    {
      title: "关注",
      dataIndex: "is_favorited",
      key: "favorite",
      width: 55,
      render: (val, record) => (
        <Tooltip title={val ? "取消关注" : "添加关注"}>
          <Button
            type="text"
            size="small"
            icon={val ? <StarFilled style={{ color: "#faad14" }} /> : <StarOutlined />}
            onClick={async (e) => {
              e.stopPropagation();
              try {
                const result = await toggleFavorite(record.id);
                message.success(result.message);
                refetch();
              } catch {
                message.error("操作失败");
              }
            }}
          />
        </Tooltip>
      ),
    },
    {
      title: "操作",
      dataIndex: "actions",
      key: "actions",
      width: 55,
      render: (_, record) => (
        <Tooltip title="删除">
          <Button
            type="text"
            size="small"
            danger
            icon={<span style={{ fontSize: 14 }}>🗑️</span>}
            onClick={(e) => {
              e.stopPropagation();
              Modal.confirm({
                title: "确认删除",
                icon: <ExclamationCircleOutlined />,
                content: `确定要删除"${record.title?.substring(0, 50)}..."吗？`,
                okText: "删除",
                okType: "danger",
                cancelText: "取消",
                onOk: async () => {
                  try {
                    await deleteAnnouncement(record.id);
                    message.success("已删除");
                    refetch();
                  } catch {
                    message.error("删除失败");
                  }
                },
              });
            }}
          />
        </Tooltip>
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
              icon={<CloudDownloadOutlined />}
              onClick={() => setProvinceModalVisible(true)}
              loading={fetching}
            >
              采集数据
            </Button>
            <Button
              icon={<DownloadOutlined />}
              onClick={() => setExportModalVisible(true)}
            >
              下载Excel
            </Button>
            <Button
              type={showFavorites ? "default" : "default"}
              icon={showFavorites ? <ArrowLeftOutlined /> : <StarOutlined />}
              onClick={() => setShowFavorites(!showFavorites)}
            >
              {showFavorites ? "返回列表" : "仅看收藏"}
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
          <Col xs={12} sm={6} md={2}>
            <Select
              value={filterProvince}
              onChange={handleProvinceChange}
              options={PROVINCE_OPTIONS}
              style={{ width: "100%" }}
              placeholder="省份"
              allowClear
            />
          </Col>
          <Col xs={12} sm={6} md={2}>
            <Select
              value={filterCity}
              onChange={setFilterCity}
              options={cityOptions}
              style={{ width: "100%" }}
              placeholder="城市"
              allowClear
              disabled={!filterProvince}
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
              value={filterNoticeType}
              onChange={setFilterNoticeType}
              options={NOTICE_TYPE_OPTIONS}
              style={{ width: "100%" }}
              placeholder="公告类型"
            />
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Select
              value={filterDataSource}
              onChange={setFilterDataSource}
              options={DATA_SOURCE_OPTIONS}
              style={{ width: "100%" }}
              placeholder="数据来源"
            />
          </Col>
          <Col xs={24} sm={12} md={5}>
            <DatePicker.RangePicker
              value={[collectedFrom, collectedTo]}
              onChange={(dates) => {
                setCollectedFrom(dates ? dates[0] : null);
                setCollectedTo(dates ? dates[1] : null);
              }}
              style={{ width: "100%" }}
              placeholder={["采集起", "采集止"]}
              allowClear
              format="YYYY-MM-DD"
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
        <Spin spinning={isLoading}>
          {data.length === 0 && !isLoading ? (
            <Empty description="暂无匹配的招标公告" />
          ) : (
            <Table
              columns={columns}
              dataSource={data}
              rowKey="id"
              pagination={{
                current: currentPage,
                pageSize: pageSize,
                showSizeChanger: true,
                showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
                total: response?.total || 0,
                onChange: (page, size) => {
                  setCurrentPage(page);
                  setPageSize(size);
                },
              }}
              scroll={{ x: 1800 }}
              size="small"
              locale={{ emptyText: "暂无数据" }}
            />
          )}
        </Spin>
      </Card>

      {/* 公告内容模态框 — 仅当成功获取到原文时显示 */}
      <Modal
        title={<span>📋 公告详情</span>}
        open={contentModalVisible}
        onCancel={handleContentModalClose}
        width={1000}
        style={{ top: 20 }}
        footer={[
          <Button key="close" onClick={handleContentModalClose}>
            关闭
          </Button>,
          contentData?.source_url && (
            <Button
              key="open"
              type="primary"
              onClick={() => window.open(contentData.source_url, '_blank')}
            >
              在 b2b.10086.cn 查看原文
            </Button>
          ),
        ]}
      >
        {contentData && (
          <div>
            <Descriptions
              title={contentData.title}
              bordered
              size="small"
              style={{marginBottom: 16}}
            >
              <Descriptions.Item label="发布日期">
                {contentData.publish_date || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="公告类型">
                {contentData.publish_type || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="公司">
                {contentData.company || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="报名截止">
                {contentData.deadline || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="投标日期">
                {contentData.bid_date || '—'}
              </Descriptions.Item>
            </Descriptions>

            <div
              style={{
                marginTop: 16,
                padding: 16,
                border: '1px solid #d9d9d9',
                borderRadius: '4px',
                backgroundColor: '#fafafa',
                maxHeight: '50vh',
                overflow: 'auto',
                lineHeight: '1.6',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word'
              }}
            >
              {contentData.notice_content || '暂无内容'}
            </div>
          </div>
        )}
      </Modal>

      {/* P3: 省份+运营商联合选择 */}
      <Modal
        title="选择采集范围"
        open={provinceModalVisible}
        onCancel={() => setProvinceModalVisible(false)}
        footer={null}
        width={520}
      >
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 500, marginBottom: 8, color: "#666" }}>📡 选择运营商</div>
          <Select
            value={selectedAdapter}
            onChange={setSelectedAdapter}
            style={{ width: "100%" }}
            options={[
              { value: "all", label: "🌐 全部运营商（移动+电信+联通）" },
              { value: "b2b_10086", label: "📶 中国移动" },
              { value: "telecom", label: "📡 中国电信" },
              { value: "unicom", label: "📞 中国联通" },
            ]}
          />
        </div>

        <div style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 500, marginBottom: 8, color: "#666" }}>📍 限定省份（可多选，留空=全国）</div>
          <Select
            mode="multiple"
            value={selectedProvinces}
            onChange={setSelectedProvinces}
            placeholder="选择省份，留空则采集全国"
            style={{ width: "100%" }}
            maxTagCount={6}
            options={PROVINCE_OPTIONS.filter(p => p.value).map(p => ({ value: p.value, label: p.label }))}
            allowClear
          />
        </div>

        <div style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 500, marginBottom: 8, color: "#666" }}><CalendarOutlined /> 采集日期范围（可选）</div>
          <DatePicker.RangePicker
            value={fetchDateRange}
            onChange={setFetchDateRange}
            style={{ width: "100%" }}
            allowClear
            placeholder={["开始日期", "结束日期"]}
          />
        </div>

        <Divider style={{ margin: "12px 0" }} />

        <Button
          type="primary"
          block
          size="large"
          icon={<CloudDownloadOutlined />}
          loading={fetching}
          onClick={() => {
            const province = selectedProvinces.join(",");
            const adapter = selectedAdapter === "all" ? "all" : selectedAdapter;
            const dateFrom = fetchDateRange?.[0]?.format("YYYY-MM-DD") || "";
            const dateTo = fetchDateRange?.[1]?.format("YYYY-MM-DD") || "";
            const dateDesc = dateFrom ? ` (${dateFrom}~${dateTo || "至今"})` : "";
            const desc = `${adapter === "all" ? "全部运营商" : adapter === "b2b_10086" ? "移动" : adapter === "telecom" ? "电信" : "联通"} × ${province || "全国"}${dateDesc}`;
            message.info(`开始采集: ${desc}`);
            startFetch(province, adapter, dateFrom, dateTo);
          }}
        >
          开始采集（{selectedAdapter === "all" ? "全部运营商" : selectedAdapter === "b2b_10086" ? "移动" : selectedAdapter === "telecom" ? "电信" : "联通"}
          {selectedProvinces.length > 0 ? ` × ${selectedProvinces.join("、")}` : " × 全国"}）
        </Button>
      </Modal>

      {/* 采集进度模态框 */}
      <Modal
        title={
          <Space>
            {fetchProgress?.status === "completed" ? (
              <CheckCircleOutlined style={{ color: "#52c41a" }} />
            ) : fetchProgress?.status === "failed" ? (
              <CloseCircleOutlined style={{ color: "#ff4d4f" }} />
            ) : (
              <LoadingOutlined spin style={{ color: "#1677ff" }} />
            )}
            <span>数据采集进度</span>
          </Space>
        }
        open={!!fetchProgress}
        footer={
          fetchProgress?.status !== "completed" && fetchProgress?.status !== "failed" ? [
            <Button key="cancel" danger onClick={() => {
              stopPolling();
              setFetchProgress(null);
              setFetching(false);
              message.info("已中止采集");
            }}>中止采集</Button>,
          ] : [
            <Button key="close" type="primary" onClick={() => {
              stopPolling();
              setFetchProgress(null);
              setFetching(false);
            }}>关闭</Button>,
          ]
        }
        closable={false}
        maskClosable={false}
        width={500}
      >
        {fetchProgress && (() => {
          // 根据 phase 计算当前步骤
          const phaseMap = { init: 0, search: 1, extract: 2, done: 3, error: -1 };
          const currentStep = phaseMap[fetchProgress.phase] ?? 0;
          const isExtracting = fetchProgress.phase === "extract";

          return (
            <div style={{ padding: "16px 0" }}>
              <Steps
                current={currentStep}
                status={
                  fetchProgress.status === "failed" ? "error"
                  : fetchProgress.status === "completed" ? "finish"
                  : "process"
                }
                size="small"
                items={[
                  { title: "初始化", description: "启动采集引擎" },
                  { title: "搜索列表", description: "扫描招标公告" },
                  { title: "提取详情", description: isExtracting ? "逐条解析中..." : "解析公告内容" },
                  { title: "入库完成", description: "数据写入数据库" },
                ]}
                style={{ marginBottom: 24 }}
              />
              <div style={{ textAlign: "center", marginBottom: 16 }}>
                <Progress
                  type="circle"
                  percent={isExtracting ? Math.round(fetchProgress.progress) : fetchProgress.progress}
                  strokeColor={
                    fetchProgress.status === "failed" ? "#ff4d4f"
                    : fetchProgress.status === "completed" ? "#52c41a"
                    : { "0%": "#108ee9", "100%": "#87d068" }
                  }
                  status={
                    fetchProgress.status === "failed" ? "exception"
                    : fetchProgress.status === "completed" ? "success"
                    : "active"
                  }
                  size={100}
                />
              </div>
              <div style={{ textAlign: "center" }}>
                <Text style={{ fontSize: 14 }}>
                  {fetchProgress.message}
                </Text>
                {isExtracting && (
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {fetchProgress.eta_seconds
                        ? `预计剩余 ${fetchProgress.eta_seconds > 60
                            ? `${Math.round(fetchProgress.eta_seconds / 60)} 分钟`
                            : `${fetchProgress.eta_seconds} 秒`}，已耗时 ${Math.round((fetchProgress.elapsed_seconds || 0) / 60)} 分钟`
                        : "正在计算预计时间..."}
                    </Text>
                  </div>
                )}
                {fetchProgress.result_count > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <Tag color="green">共采集 {fetchProgress.result_count} 条公告</Tag>
                  </div>
                )}
                {fetchProgress.status === "failed" && fetchProgress.error && (
                  <div style={{ marginTop: 8 }}>
                    <Text type="danger" style={{ fontSize: 12 }}>{fetchProgress.error}</Text>
                  </div>
                )}
              </div>
            </div>
          );
        })()}
      </Modal>

      {/* 选择导出范围弹窗 */}
      <Modal
        title="导出 Excel"
        open={exportModalVisible}
        onCancel={() => setExportModalVisible(false)}
        footer={null}
        width={360}
      >
        <div style={{ padding: "16px 0", textAlign: "center" }}>
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            <Button
              type="primary"
              block
              size="large"
              icon={<DownloadOutlined />}
              onClick={() => {
                const filters = {
                  notice_type: filterNoticeType || undefined,
                  budget_min: budgetRange[0] || undefined,
                  budget_max: budgetRange[1] || undefined,
                  project_category: filterCategory || undefined,
                  procurement_method: filterMethod || undefined,
                  province: filterProvince || undefined,
                  search: searchText || undefined,
                };
                window.open(exportFavoritesUrl(false, filters), '_blank');
                setExportModalVisible(false);
              }}
            >
              导出全部公告（跟随筛选）
            </Button>
            <Button
              block
              size="large"
              icon={<StarOutlined />}
              onClick={() => {
                const filters = {
                  notice_type: filterNoticeType || undefined,
                  budget_min: budgetRange[0] || undefined,
                  budget_max: budgetRange[1] || undefined,
                };
                window.open(exportFavoritesUrl(true, filters), '_blank');
                setExportModalVisible(false);
              }}
            >
              仅导出收藏项目
            </Button>
          </Space>
        </div>
      </Modal>
    </div>
  );
}

export default OpportunityList;
