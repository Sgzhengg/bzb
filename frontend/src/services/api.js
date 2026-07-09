import axios from "axios";

const apiClient = axios.create({
  baseURL: "http://localhost:8000/api/v1",
  timeout: 15000,
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
 * 获取 b2b.10086.cn 公告原文
 * 通过 b2b API 搜索并返回公告详情和搜索链接
 */
export async function getAnnouncementOriginal(id) {
  return apiClient.get(`/announcements/${id}/original`);
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

// ============================================================
// 用户偏好 API
// ============================================================

export async function getPreferences() {
  return apiClient.get("/preferences");
}

export async function updatePreferences(data) {
  return apiClient.put("/preferences", data);
}

export async function resetPreferences() {
  return apiClient.delete("/preferences");
}

// ============================================================
// 收藏 API
// ============================================================

export async function toggleFavorite(id) {
  return apiClient.post(`/announcements/${id}/favorite`);
}

export async function getFavorites(params = {}) {
  return apiClient.get("/announcements/favorites", { params });
}

// ============================================================
// 图表数据 API
// ============================================================

export async function getChartData(chartType, params = {}) {
  return apiClient.get(`/charts/json/${chartType}`, { params });
}

export async function getChartTypes() {
  return apiClient.get("/charts/types");
}

// ============================================================
// 调度器 API
// ============================================================

export async function getSchedulerStatus() {
  return apiClient.get("/scheduler/status");
}

export async function startScheduler() {
  return apiClient.post("/scheduler/start");
}

export async function triggerJob(jobId) {
  return apiClient.post(`/scheduler/trigger/${jobId}`);
}

// ============================================================
// 提醒 API
// ============================================================

export async function getUnreadAlertCount() {
  return apiClient.get("/alerts/unread-count");
}

export async function markAlertRead(alertId) {
  return apiClient.put(`/alerts/${alertId}/read`);
}

// ============================================================
// 统计概览 API
// ============================================================

export async function getDashboardStats() {
  // 聚合多个API获取仪表盘数据
  const [health, alerts, announcements] = await Promise.allSettled([
    apiClient.get("/health"),
    apiClient.get("/alerts/unread-count"),
    apiClient.get("/announcements", { params: { page_size: 5 } }),
  ]);

  return {
    health: health.status === "fulfilled" ? health.value : null,
    unreadAlerts: alerts.status === "fulfilled" ? alerts.value?.unread_count || 0 : 0,
    recentAnnouncements: announcements.status === "fulfilled"
      ? announcements.value?.items || []
      : [],
  };
}

// ============================================================
// 预算抓取 API（zhaobiao.cn 登录后自动提取）
// ============================================================

/**
 * 启动预算抓取任务
 */
export async function startBudgetScrape() {
  return apiClient.post("/announcements/scrape-budget/start");
}

/**
 * 查询抓取进度
 */
export async function getBudgetScrapeStatus() {
  return apiClient.get("/announcements/scrape-budget/status");
}

/**
 * LLM 提取单条公告预算
 */
export async function extractBudget(id) {
  return apiClient.post(`/announcements/extract-budget/${id}`);
}

/**
 * LLM 批量提取预算（所有无预算的公告）
 */
export async function extractBudgetBatch(limit = 10) {
  return apiClient.post("/announcements/extract-budget/batch", null, {
    params: { limit },
  });
}

// ============================================================
// LLM 配置 API
// ============================================================

export async function saveLLMConfig(config) {
  return apiClient.put("/preferences", {
    ...config,
    // LLM config stored as part of preferences
  });
}
