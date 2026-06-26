import axios from "axios";

const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1",
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可在此添加 Token 等认证信息
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error("API 请求错误:", error);
    return Promise.reject(error);
  }
);

/**
 * 健康检查
 */
export async function getHealthStatus() {
  return apiClient.get("/health");
}

/**
 * 获取招标列表（Mock 数据）
 */
export async function getMockBiddingData() {
  // 当后端未就绪时，返回 Mock 数据用于前端开发
  return [
    {
      id: 1,
      projectName: "中国移动广东公司2024年度广告投放服务采购项目",
      purchaser: "中国移动通信集团广东有限公司",
      budget: "500万元",
      publishDate: "2024-01-15",
      status: "招标中",
    },
    {
      id: 2,
      projectName: "广东移动2024年品牌传播策划服务招标",
      purchaser: "中国移动通信集团广东有限公司",
      budget: "300万元",
      publishDate: "2024-01-10",
      status: "招标中",
    },
    {
      id: 3,
      projectName: "广东移动新媒体运营支撑服务项目",
      purchaser: "中国移动通信集团广东有限公司",
      budget: "200万元",
      publishDate: "2023-12-20",
      status: "已中标",
    },
    {
      id: 4,
      projectName: "中国移动广东公司营业厅宣传物料设计制作项目",
      purchaser: "中国移动通信集团广东有限公司",
      budget: "150万元",
      publishDate: "2023-12-05",
      status: "已截止",
    },
    {
      id: 5,
      projectName: "广东移动2024年度线上广告投放代理服务",
      purchaser: "中国移动通信集团广东有限公司",
      budget: "800万元",
      publishDate: "2024-02-01",
      status: "招标中",
    },
  ];
}

export default apiClient;

// ============================================================
// 招标公告 API
// ============================================================

/**
 * 获取机会列表（按推荐指数降序）
 */
export async function getOpportunityList(params = {}) {
  return apiClient.get("/announcements", { params });
}

/**
 * 触发数据采集
 */
export async function fetchNewAnnouncements() {
  return apiClient.post("/announcements/fetch");
}

/**
 * 获取公告详情
 */
export async function getAnnouncementDetail(id) {
  return apiClient.get(`/announcements/${id}`);
}

/**
 * 获取公告的关联提醒
 */
export async function getAnnouncementAlerts(id) {
  return apiClient.get(`/alerts/announcement/${id}`);
}

/**
 * 获取采购方列表（用于筛选器）
 */
export async function getPurchasers() {
  return apiClient.get("/purchasers");
}

/**
 * 获取采购方画像详情
 */
export async function getPurchaserProfile(id) {
  return apiClient.get(`/purchasers/${id}/profile`);
}

// ============================================================
// 客情管理 API
// ============================================================

/**
 * 获取客情列表
 */
export async function getRelations(params = {}) {
  return apiClient.get("/relations", { params });
}

/**
 * 获取今日跟进提醒
 */
export async function getRelationReminders() {
  return apiClient.get("/relations/reminders");
}

/**
 * 创建客情记录
 */
export async function createRelation(data) {
  return apiClient.post("/relations", data);
}

/**
 * 更新客情记录
 */
export async function updateRelation(id, data) {
  return apiClient.put(`/relations/${id}`, data);
}

/**
 * 删除客情记录
 */
export async function deleteRelation(id) {
  return apiClient.delete(`/relations/${id}`);
}
