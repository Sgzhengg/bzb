import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Card, Table, Tag, Button, Space, Input, Select, Modal, Form,
  DatePicker, InputNumber, Row, Col, Typography, Popconfirm, message,
  Statistic, Badge, Collapse, Tooltip, Empty, Spin,
} from "antd";
import {
  PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined,
  BellOutlined, UserOutlined, PhoneOutlined, EnvironmentOutlined,
  ReloadOutlined, StarFilled,
} from "@ant-design/icons";
import {
  getRelations, getRelationReminders,
  createRelation, updateRelation, deleteRelation,
  getPurchasers,
} from "../services/api";

const { Title, Text } = Typography;
const { TextArea } = Input;

// 评级颜色
const RATING_COLORS = { S: "#f50", A: "#fa8c16", B: "#1890ff", C: "#52c41a", D: "#d9d9d9" };
const RATING_LABELS = { S: "S · 极好", A: "A · 好", B: "B · 较好", C: "C · 一般", D: "D · 差" };
const RATING_ORDER = { S: 0, A: 1, B: 2, C: 3, D: 4 };

// 全省21个地市
const ALL_CITIES = [
  "广州", "深圳", "东莞", "佛山", "珠海", "中山", "惠州",
  "汕头", "江门", "湛江", "茂名", "肇庆", "梅州", "汕尾",
  "河源", "阳江", "清远", "潮州", "揭阳", "云浮", "韶关",
];

function RelationManagement() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [filterRating, setFilterRating] = useState("");
  const [purchasers, setPurchasers] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [reminderTotal, setReminderTotal] = useState(0);

  // 表单
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (searchText) params.search = searchText;
      if (filterRating) params.rating = filterRating;
      const result = await getRelations(params);
      const items = result?.items || result || [];
      // 评级排序
      items.sort((a, b) => (RATING_ORDER[a.rating] ?? 5) - (RATING_ORDER[b.rating] ?? 5));
      setData(items);
    } catch {
      message.error("加载客情列表失败");
    } finally {
      setLoading(false);
    }
  }, [searchText, filterRating]);

  const loadReminders = useCallback(async () => {
    try {
      const result = await getRelationReminders();
      const items = Array.isArray(result) ? result : result?.items || [];
      setReminders(items);
      setReminderTotal(items.length);
    } catch { /* 后端不可用，忽略 */ }
  }, []);

  const loadPurchasers = useCallback(async () => {
    try {
      const result = await getPurchasers();
      const list = Array.isArray(result) ? result : result?.items || [];
      setPurchasers(list);
    } catch { /* 忽略 */ }
  }, []);

  useEffect(() => { loadData(); loadReminders(); loadPurchasers(); }, [loadData, loadReminders, loadPurchasers]);

  // 打开创建表单
  const openCreate = () => {
    setEditingId(null);
    form.resetFields();
    form.setFieldsValue({ rating: "C" });
    setModalOpen(true);
  };

  // 打开编辑表单
  const openEdit = (record) => {
    setEditingId(record.id);
    form.setFieldsValue({
      purchaser_id: record.purchaser_id,
      contact_name: record.contact_name,
      title: record.title,
      phone: record.phone,
      email: record.email,
      rating: record.rating,
      contact_method: record.contact_method,
      contact_summary: record.contact_summary,
      last_contact_date: record.last_contact_date || undefined,
      next_followup_date: record.next_followup_date || undefined,
    });
    setModalOpen(true);
  };

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      const payload = {
        ...values,
        last_contact_date: values.last_contact_date?.format?.("YYYY-MM-DD") || values.last_contact_date,
        next_followup_date: values.next_followup_date?.format?.("YYYY-MM-DD") || values.next_followup_date,
      };
      if (editingId) {
        await updateRelation(editingId, payload);
        message.success("更新成功");
      } else {
        await createRelation(payload);
        message.success("创建成功");
      }
      setModalOpen(false);
      loadData();
      loadReminders();
    } catch (err) {
      if (err?.errorFields) return; // 表单校验错误
      message.error("操作失败");
    } finally {
      setSubmitting(false);
    }
  };

  // 删除
  const handleDelete = async (id) => {
    try {
      await deleteRelation(id);
      message.success("删除成功");
      loadData();
      loadReminders();
    } catch {
      message.error("删除失败");
    }
  };

  // 客情覆盖计算
  const coverageStats = useMemo(() => {
    const citiesWithRelations = new Set();
    const cityRatingMap = {};
    if (purchasers.length > 0 && data.length > 0) {
      data.forEach(rel => {
        const p = purchasers.find(pp => (pp.id || pp.purchaser_id) === rel.purchaser_id);
        if (p?.region) {
          citiesWithRelations.add(p.region);
          const existing = cityRatingMap[p.region];
          if (!existing || (RATING_ORDER[rel.rating] ?? 5) < (RATING_ORDER[existing] ?? 5)) {
            cityRatingMap[p.region] = rel.rating;
          }
        }
      });
    }
    return { covered: citiesWithRelations.size, total: 21, cityRatingMap };
  }, [data, purchasers]);

  // 表格列
  const columns = [
    {
      title: "采购方", dataIndex: "purchaser_id", key: "purchaser", width: 140,
      render: (pid) => {
        const p = purchasers.find(pp => (pp.id || pp.purchaser_id) === pid);
        return <Text>{p?.name || `采购方${pid}`}</Text>;
      },
    },
    { title: "联系人", dataIndex: "contact_name", key: "contact_name", width: 100 },
    { title: "职位", dataIndex: "title", key: "title", width: 100, render: (t) => t || "—" },
    {
      title: "电话", dataIndex: "phone", key: "phone", width: 120,
      render: (p) => p ? <Text copyable>{p}</Text> : "—",
    },
    {
      title: "最近接触", dataIndex: "last_contact_date", key: "last_contact_date", width: 110,
      sorter: (a, b) => (a.last_contact_date || "").localeCompare(b.last_contact_date || ""),
      render: (d) => d || <Text type="secondary">—</Text>,
    },
    {
      title: "评级", dataIndex: "rating", key: "rating", width: 100,
      render: (r) => <Tag color={RATING_COLORS[r]}>{RATING_LABELS[r] || r}</Tag>,
    },
    {
      title: "下次跟进", dataIndex: "next_followup_date", key: "next_followup_date", width: 110,
      render: (d) => {
        if (!d) return <Text type="secondary">—</Text>;
        const days = Math.ceil((new Date(d) - new Date()) / 86400000);
        if (days < 0) return <Tag color="default">已过期</Tag>;
        if (days === 0) return <Tag color="red">今天</Tag>;
        return <Text>{d} <Text type="secondary">({days}天后)</Text></Text>;
      },
    },
    {
      title: "操作", key: "actions", width: 120, fixed: "right",
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除此客情记录？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}><UserOutlined /> 客情管理</Title>

      {/* ── 今日提醒 + 客情覆盖 ── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} md={14}>
          <Card size="small">
            <Row align="middle" justify="space-between">
              <Col>
                <Space size={16}>
                  <Statistic
                    title={<><BellOutlined /> 今日需跟进</>}
                    value={reminderTotal}
                    suffix="位客户"
                    valueStyle={{ color: reminderTotal > 0 ? "#fa8c16" : "#999", fontSize: 24 }}
                  />
                  {reminders.length > 0 && (
                    <Collapse ghost size="small" items={[{
                      key: "1",
                      label: <Text type="secondary">展开查看</Text>,
                      children: (
                        <div style={{ maxHeight: 200, overflow: "auto" }}>
                          {reminders.map((r, i) => (
                            <div key={i} style={{ padding: "4px 0", borderBottom: "1px solid #f0f0f0" }}>
                              <Space>
                                <Tag color={RATING_COLORS[r.rating]}>{r.rating}</Tag>
                                <Text strong>{r.contact_name}</Text>
                                {r.title && <Text type="secondary">({r.title})</Text>}
                                {r.phone && <Text copyable style={{ fontSize: 12 }}>{r.phone}</Text>}
                              </Space>
                            </div>
                          ))}
                        </div>
                      ),
                    }]} />
                  )}
                </Space>
              </Col>
            </Row>
          </Card>
        </Col>
        <Col xs={24} md={10}>
          <Card size="small" title={<><EnvironmentOutlined /> 客情覆盖</>}>
            <div style={{ textAlign: "center", marginBottom: 8 }}>
              <Text style={{ fontSize: 28, fontWeight: "bold", color: "#1677ff" }}>
                {coverageStats.covered}
              </Text>
              <Text style={{ fontSize: 18 }}> / 21</Text>
              <Text type="secondary" style={{ marginLeft: 8 }}>个地市</Text>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {ALL_CITIES.map(city => {
                const rating = coverageStats.cityRatingMap[city];
                return (
                  <Tooltip key={city} title={rating ? `评级: ${rating}` : "未覆盖"}>
                    <Tag color={rating ? RATING_COLORS[rating] : "#f0f0f0"}
                         style={{ opacity: rating ? 1 : 0.4 }}>
                      {city}
                    </Tag>
                  </Tooltip>
                );
              })}
            </div>
          </Card>
        </Col>
      </Row>

      {/* ── 搜索筛选栏 ── */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col xs={24} sm={8}>
            <Input prefix={<SearchOutlined />} placeholder="搜索采购方或联系人..."
              value={searchText} onChange={e => setSearchText(e.target.value)} allowClear />
          </Col>
          <Col xs={12} sm={4}>
            <Select value={filterRating} onChange={setFilterRating}
              options={[{ value: "", label: "全部评级" },
                ...Object.entries(RATING_LABELS).map(([k, v]) => ({ value: k, label: v }))]}
              style={{ width: "100%" }} />
          </Col>
          <Col>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={() => { loadData(); loadReminders(); }}>刷新</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增客情</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* ── 数据表格 ── */}
      <Card>
        <Spin spinning={loading}>
          {data.length === 0 && !loading ? (
            <Empty description={'暂无客情记录，点击"新增客情"开始建立'} />
          ) : (
            <Table columns={columns} dataSource={data} rowKey="id"
              pagination={{ pageSize: 20, showTotal: t => `共 ${t} 条` }}
              scroll={{ x: 1000 }} size="middle" />
          )}
        </Spin>
      </Card>

      {/* ── 编辑/新增弹窗 ── */}
      <Modal
        title={editingId ? "编辑客情记录" : "新增客情记录"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={submitting}
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="purchaser_id" label="采购方" rules={[{ required: true, message: "请选择采购方" }]}>
                <Select showSearch placeholder="选择采购方"
                  filterOption={(input, option) => option.children?.toLowerCase().includes(input.toLowerCase())}
                  options={purchasers.map(p => ({
                    value: p.id || p.purchaser_id,
                    label: `${p.name} (${p.level || ""} · ${p.region || ""})`,
                  }))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="contact_name" label="联系人姓名" rules={[{ required: true, message: "请输入姓名" }]}>
                <Input placeholder="联系人姓名" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="title" label="职位"><Input placeholder="如：采购经理" /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="phone" label="电话"><Input placeholder="手机号" /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="email" label="邮箱" rules={[{ type: "email", message: "邮箱格式不正确" }]}>
                <Input placeholder="email@example.com" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="rating" label="关系评级" rules={[{ required: true }]}>
                <Select options={Object.entries(RATING_LABELS).map(([k, v]) => ({ value: k, label: v }))} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="contact_method" label="接触方式">
                <Select placeholder="选择接触方式" options={[
                  { value: "面谈", label: "面谈" }, { value: "电话", label: "电话" },
                  { value: "微信", label: "微信" }, { value: "邮件", label: "邮件" },
                  { value: "饭局", label: "饭局" },
                ]} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="last_contact_date" label="最近接触时间">
                <DatePicker style={{ width: "100%" }} placeholder="选择日期" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="contact_summary" label="接触内容摘要">
            <TextArea rows={3} placeholder="简要记录沟通内容和关键信息..." />
          </Form.Item>
          <Form.Item name="next_followup_date" label="下次跟进提醒日期">
            <DatePicker style={{ width: "100%" }} placeholder="设置跟进提醒日期" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default RelationManagement;
