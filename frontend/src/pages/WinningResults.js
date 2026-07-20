import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Card, Table, Tag, Typography, Row, Col,
  Input, Button, Space, Spin, Empty, App, Popconfirm, Select,
  Modal, Progress, Divider,
} from "antd";
import {
  TrophyOutlined, SearchOutlined,
  ReloadOutlined, LinkOutlined, CloudDownloadOutlined, DownloadOutlined,
  LoadingOutlined, CheckCircleOutlined, CloseCircleOutlined,
} from "@ant-design/icons";
import apiClient from "../services/api";

const { Title, Text } = Typography;

function WinningResults() {
  const { message } = App.useApp();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState("");
  const [filterDataSource, setFilterDataSource] = useState("");
  const [fetching, setFetching] = useState(false);
  const [provinceModalVisible, setProvinceModalVisible] = useState(false);
  const [selectedAdapter, setSelectedAdapter] = useState("b2b_10086");
  const [selectedProvinces, setSelectedProvinces] = useState([]);

  // 采集进度状态
  const [fetchProgress, setFetchProgress] = useState(null);
  const progressTimer = useRef(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (searchText) params.search = searchText;
      if (filterDataSource) params.data_source = filterDataSource;
      const result = await apiClient.get("/awards", { params });
      setData(result.items || []);
    } catch {
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [searchText, filterDataSource]);

  useEffect(() => { loadData(); }, [loadData]);

  // 清理定时器
  useEffect(() => () => {
    if (progressTimer.current) clearInterval(progressTimer.current);
  }, []);

  const handleDelete = async (id, projectName) => {
    try {
      await apiClient.delete(`/awards/${id}`);
      message.success(`已删除: ${projectName}`);
      loadData();
    } catch {
      message.error("删除失败，请重试");
    }
  };

  const dataSourceOptions = [
    { value: "", label: "全部来源" },
    { value: "b2b_10086", label: "中国移动" },
    { value: "telecom", label: "中国电信" },
    { value: "unicom", label: "中国联通" },
    { value: "gd_zbtb", label: "广东招标监管网" },
    { value: "gd_ygp", label: "广东公共资源平台" },
  ];

  const startFetch = async (province, adapter = "") => {
    setProvinceModalVisible(false);
    setFetching(true);
    try {
      const params = province ? { province } : {};
      if (adapter) params.adapter = adapter;
      const result = await apiClient.post("/awards/fetch", null, { params });
      if (result.task_id) {
        setFetchProgress({
          taskId: result.task_id,
          status: "starting",
          progress: 0,
          message: result.message || "正在启动...",
        });

        progressTimer.current = setInterval(async () => {
          try {
            const status = await apiClient.get(`/awards/fetch/status/${result.task_id}`);
            setFetchProgress(prev => ({ ...prev, ...status }));

            if (status.status === "completed") {
              clearInterval(progressTimer.current);
              message.success(status.message || "中标结果采集完成！");
              setTimeout(() => {
                window._bzbCheckNew?.();
                setFetchProgress(null);
                setFetching(false);
                loadData();
              }, 2000);
            } else if (status.status === "failed") {
              clearInterval(progressTimer.current);
              message.error(status.message || "采集失败");
              setTimeout(() => {
                setFetchProgress(null);
                setFetching(false);
              }, 3000);
            }
          } catch (err) {
            if (err?.response?.status === 404) {
              clearInterval(progressTimer.current);
              setFetchProgress(null);
              setFetching(false);
              message.warning("任务已过期，请重新采集");
            }
          }
        }, 1500);
      } else {
        message.success(result.message || "采集任务已启动");
        setFetching(false);
        setTimeout(() => loadData(), 5000);
      }
    } catch {
      message.error("启动采集失败");
      setFetching(false);
    }
  };

  // P3: 添加数据来源列
  const columns = [
    {
      title: "来源", dataIndex: "data_source", key: "data_source", width: 90,
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
      title: "项目名称", dataIndex: "project_name", key: "project_name",
      width: 300, ellipsis: true,
    },
    {
      title: "中标方", dataIndex: "winner_name", key: "winner", width: 160,
      render: (v) => <Text strong>{v}</Text>,
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
          <Button type="link" danger size="small" icon={<span>🗑️</span>} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}><TrophyOutlined /> 中标结果</Title>
        </Col>
        <Col>
          <Space>
            <Button icon={<CloudDownloadOutlined />} onClick={() => setProvinceModalVisible(true)} loading={fetching}>
              采集数据
            </Button>
            <Button icon={<DownloadOutlined />}
              onClick={() => {
                const base = apiClient.defaults.baseURL;
                const url = (base.startsWith("http") ? base : window.location.origin + base) + "/awards/export";
                window.open(url, '_blank');
              }}>
              下载Excel
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 筛选栏 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col xs={24} sm={12} md={6}>
            <Input prefix={<SearchOutlined />} placeholder="搜索项目/中标方..."
              value={searchText} onChange={e => setSearchText(e.target.value)} allowClear />
          </Col>
          <Col xs={24} sm={12} md={4}>
            <Select placeholder="数据来源" value={filterDataSource} onChange={setFilterDataSource}
              options={dataSourceOptions} style={{ width: "100%" }} allowClear />
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

      {/* 选择采集范围弹窗 */}
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
            options={["广东","广西","福建","海南","浙江","湖南","江苏","四川","湖北","北京","上海","安徽","山东","河南"].map(p => ({ value: p, label: p }))}
            allowClear
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
            const desc = `${adapter === "all" ? "全部运营商" : selectedAdapter === "b2b_10086" ? "移动" : selectedAdapter === "telecom" ? "电信" : "联通"} × ${province || "全国"}`;
            message.info(`开始采集: ${desc}`);
            startFetch(province, adapter);
          }}
        >
          开始采集（{selectedAdapter === "all" ? "全部运营商" : selectedAdapter === "b2b_10086" ? "移动" : selectedAdapter === "telecom" ? "电信" : "联通"}
          {selectedProvinces.length > 0 ? ` × ${selectedProvinces.join("、")}` : " × 全国"}）
        </Button>
      </Modal>

      {/* 采集进度弹窗 */}
      <Modal
        title={
          <Space>
            {fetchProgress?.status === "completed" ? (
              <CheckCircleOutlined style={{ color: "#52c41a" }} />
            ) : (
              <LoadingOutlined spin style={{ color: "#1677ff" }} />
            )}
            <span>数据采集进度</span>
          </Space>
        }
        open={!!fetchProgress}
        footer={
          fetchProgress?.status !== "completed" ? [
            <Button key="cancel" danger onClick={() => {
              if (progressTimer.current) clearInterval(progressTimer.current);
              setFetchProgress(null);
              setFetching(false);
              message.info("已中止采集");
            }}>中止采集</Button>,
          ] : [
            <Button key="close" type="primary" onClick={() => {
              setFetchProgress(null);
              setFetching(false);
            }}>关闭</Button>,
          ]
        }
        closable={false}
        maskClosable={false}
        width={500}
      >
        {fetchProgress && (
          <div style={{ padding: "16px 0" }}>
            <div style={{ textAlign: "center", marginBottom: 16 }}>
              <Progress
                type="circle"
                percent={fetchProgress.progress || 0}
                strokeColor={
                  fetchProgress.status === "completed" ? "#52c41a"
                  : { "0%": "#108ee9", "100%": "#87d068" }
                }
                status={fetchProgress.status === "completed" ? "success" : "active"}
                size={100}
              />
            </div>
            <div style={{ textAlign: "center" }}>
              <Text style={{ fontSize: 14 }}>{fetchProgress.message}</Text>
              {fetchProgress.status !== "completed" && (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    此过程需要 1-3 分钟，请耐心等待...
                  </Text>
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

export default WinningResults;
