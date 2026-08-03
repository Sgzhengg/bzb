import axios from "axios";

const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || "/api/v1",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 自动附加 Token
    const token = localStorage.getItem("bzb_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // 401 是未登录的正常状态，不打印错误日志
    if (error.response?.status !== 401) {
      console.error("API 请求错误:", error);
    }
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
 * 触发数据采集（后台异步，立即返回）
 * @param {string} province - 目标省份，默认广东
 * @param {string} adapter - 指定适配器: b2b_10086(移动)/telecom(电信)/unicom(联通)/all(全部)
 */
export async function fetchNewAnnouncements(province = "", adapter = "", dateFrom = "", dateTo = "", category = "", city = "") {
  const params = {};
  if (adapter) {
    params.adapter = adapter;
  }
  if (category) {
    params.category = category;
  }
  if (province) {
    params.province = province;
  }
  if (city) {
    params.city = city;
  }
  if (dateFrom) {
    params.date_from = dateFrom;
  }
  if (dateTo) {
    params.date_to = dateTo;
  }
  return apiClient.post("/announcements/fetch", null, {
    params,
    timeout: 30000,
  });
}

/**
 * 查询采集进度
 */
export async function getFetchStatus(taskId) {
  return apiClient.get(`/announcements/fetch/status/${taskId}`);
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
 * 获取公告 AI 智能摘要 + 资格预审分析
 */
export async function getAISummary(id, forceRefresh = false) {
  return apiClient.get(`/announcements/${id}/ai-summary`, {
    params: { force_refresh: forceRefresh },
    timeout: 45000,
  });
}

/**
 * 批量生成 AI 摘要
 */
export async function batchAISummary(limit = 20, forceRefresh = false) {
  return apiClient.post("/announcements/ai-summary/batch", null, {
    params: { limit, force_refresh: forceRefresh },
  });
}

/**
 * 查询批量 AI 摘要进度
 */
export async function getBatchAISummaryStatus(taskId) {
  return apiClient.get(`/announcements/ai-summary/batch/status/${taskId}`);
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

export async function deleteAnnouncement(id) {
  return apiClient.delete(`/announcements/${id}`);
}

export function exportFavoritesUrl(favoritesOnly = false, filters = {}) {
  const base = process.env.REACT_APP_API_URL || "/api/v1";
  const absolute = base.startsWith("http") ? base : window.location.origin + base;
  const params = new URLSearchParams();
  if (favoritesOnly) params.set("favorites_only", "true");
  if (filters.notice_type) params.set("notice_type", filters.notice_type);
  if (filters.budget_min != null) params.set("budget_min", filters.budget_min);
  if (filters.budget_max != null) params.set("budget_max", filters.budget_max);
  if (filters.project_category) params.set("project_category", filters.project_category);
  if (filters.procurement_method) params.set("procurement_method", filters.procurement_method);
  if (filters.province) params.set("province", filters.province);
  if (filters.city) params.set("city", filters.city);
  if (filters.data_source) params.set("data_source", filters.data_source);
  if (filters.collected_from) params.set("collected_from", filters.collected_from);
  if (filters.collected_to) params.set("collected_to", filters.collected_to);
  if (filters.search) params.set("search", filters.search);
  const qs = params.toString();
  return absolute + "/announcements/favorites/export" + (qs ? "?" + qs : "");
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
