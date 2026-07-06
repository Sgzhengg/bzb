/**
 * React Query API Hooks - 标中宝前端
 * 使用 React Query 管理所有 API 调用，提供自动缓存、重试、后台更新等功能
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./api";

// ============================================================
// 招标公告 Hooks
// ============================================================

/**
 * 获取机会列表
 */
export function useOpportunityList(params = {}, queryOptions = {}) {
  return useQuery({
    queryKey: ["opportunities", params],
    queryFn: () => apiClient.get("/announcements", { params }),
    ...queryOptions,
  });
}

/**
 * 获取公告详情
 */
export function useAnnouncementDetail(id, queryOptions = {}) {
  return useQuery({
    queryKey: ["announcement", id],
    queryFn: () => apiClient.get(`/announcements/${id}`),
    enabled: !!id, // 只有 id 存在时才执行
    ...queryOptions,
  });
}

/**
 * 获取收藏列表
 */
export function useFavorites(params = {}, queryOptions = {}) {
  return useQuery({
    queryKey: ["favorites", params],
    queryFn: () => apiClient.get("/announcements/favorites", { params }),
    ...queryOptions,
  });
}

/**
 * 触发数据采集（Mutation）
 */
export function useFetchAnnouncements() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiClient.post("/announcements/fetch"),
    onSuccess: () => {
      // 采集完成后刷新机会列表
      queryClient.invalidateQueries({ queryKey: ["opportunities"] });
      queryClient.invalidateQueries({ queryKey: ["favorites"] });
    },
  });
}

/**
 * 切换收藏状态（Mutation）
 */
export function useToggleFavorite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => apiClient.post(`/announcements/${id}/favorite`),
    onSuccess: (data, variables) => {
      // 收藏操作后刷新相关查询
      queryClient.invalidateQueries({ queryKey: ["announcement", variables] });
      queryClient.invalidateQueries({ queryKey: ["favorites"] });
      queryClient.invalidateQueries({ queryKey: ["opportunities"] });
    },
  });
}

// ============================================================
// 客情管理 Hooks
// ============================================================

/**
 * 获取客情列表
 */
export function useRelations(params = {}, queryOptions = {}) {
  return useQuery({
    queryKey: ["relations", params],
    queryFn: () => apiClient.get("/relations", { params }),
    ...queryOptions,
  });
}

/**
 * 获取今日跟进提醒
 */
export function useRelationReminders(queryOptions = {}) {
  return useQuery({
    queryKey: ["relation-reminders"],
    queryFn: () => apiClient.get("/relations/reminders"),
    staleTime: 2 * 60 * 1000, // 提醒数据保持 2 分钟新鲜
    ...queryOptions,
  });
}

/**
 * 创建客情记录（Mutation）
 */
export function useCreateRelation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => apiClient.post("/relations", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["relations"] });
      queryClient.invalidateQueries({ queryKey: ["relation-reminders"] });
    },
  });
}

/**
 * 更新客情记录（Mutation）
 */
export function useUpdateRelation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => apiClient.put(`/relations/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["relations"] });
      queryClient.invalidateQueries({ queryKey: ["relation-reminders"] });
    },
  });
}

/**
 * 删除客情记录（Mutation）
 */
export function useDeleteRelation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => apiClient.delete(`/relations/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["relations"] });
      queryClient.invalidateQueries({ queryKey: ["relation-reminders"] });
    },
  });
}

// ============================================================
// 提醒 Hooks
// ============================================================

/**
 * 获取未读提醒数量
 */
export function useUnreadAlertCount(queryOptions = {}) {
  return useQuery({
    queryKey: ["unread-alert-count"],
    queryFn: () => apiClient.get("/alerts/unread-count"),
    refetchInterval: 60 * 1000, // 每分钟自动刷新
    staleTime: 30 * 1000, // 30 秒内数据视为新鲜
    ...queryOptions,
  });
}

/**
 * 标记提醒已读（Mutation）
 */
export function useMarkAlertRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (alertId) => apiClient.put(`/alerts/${alertId}/read`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["unread-alert-count"] });
    },
  });
}

/**
 * 获取公告的关联提醒
 */
export function useAnnouncementAlerts(announcementId, queryOptions = {}) {
  return useQuery({
    queryKey: ["announcement-alerts", announcementId],
    queryFn: () => apiClient.get(`/alerts/announcement/${announcementId}`),
    enabled: !!announcementId,
    ...queryOptions,
  });
}

// ============================================================
// 采购方 Hooks
// ============================================================

/**
 * 获取采购方列表
 */
export function usePurchasers(queryOptions = {}) {
  return useQuery({
    queryKey: ["purchasers"],
    queryFn: () => apiClient.get("/purchasers"),
    staleTime: 10 * 60 * 1000, // 10 分钟内数据视为新鲜
    ...queryOptions,
  });
}

/**
 * 获取采购方画像
 */
export function usePurchaserProfile(purchaserId, queryOptions = {}) {
  return useQuery({
    queryKey: ["purchaser-profile", purchaserId],
    queryFn: () => apiClient.get(`/purchasers/${purchaserId}/profile`),
    enabled: !!purchaserId,
    staleTime: 5 * 60 * 1000, // 5 分钟内数据视为新鲜
    ...queryOptions,
  });
}

// ============================================================
// 图表数据 Hooks
// ============================================================

/**
 * 获取图表数据
 */
export function useChartData(chartType, params = {}, queryOptions = {}) {
  return useQuery({
    queryKey: ["chart", chartType, params],
    queryFn: () => apiClient.get(`/charts/json/${chartType}`, { params }),
    staleTime: 10 * 60 * 1000, // 图表数据 10 分钟新鲜
    ...queryOptions,
  });
}

/**
 * 获取图表类型列表
 */
export function useChartTypes(queryOptions = {}) {
  return useQuery({
    queryKey: ["chart-types"],
    queryFn: () => apiClient.get("/charts/types"),
    ...queryOptions,
  });
}

// ============================================================
// 用户偏好 Hooks
// ============================================================

/**
 * 获取用户偏好
 */
export function usePreferences(queryOptions = {}) {
  return useQuery({
    queryKey: ["preferences"],
    queryFn: () => apiClient.get("/preferences"),
    staleTime: 30 * 60 * 1000, // 30 分钟内数据视为新鲜
    ...queryOptions,
  });
}

/**
 * 更新用户偏好（Mutation）
 */
export function useUpdatePreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => apiClient.put("/preferences", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["preferences"] });
    },
  });
}

/**
 * 重置用户偏好（Mutation）
 */
export function useResetPreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiClient.delete("/preferences"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["preferences"] });
    },
  });
}

// ============================================================
// 调度器 Hooks
// ============================================================

/**
 * 获取调度器状态
 */
export function useSchedulerStatus(queryOptions = {}) {
  return useQuery({
    queryKey: ["scheduler-status"],
    queryFn: () => apiClient.get("/scheduler/status"),
    refetchInterval: 30 * 1000, // 每 30 秒刷新
    ...queryOptions,
  });
}

/**
 * 启动调度器（Mutation）
 */
export function useStartScheduler() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiClient.post("/scheduler/start"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scheduler-status"] });
    },
  });
}

/**
 * 停止调度器（Mutation）
 */
export function useStopScheduler() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiClient.post("/scheduler/stop"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scheduler-status"] });
    },
  });
}

/**
 * 触发任务（Mutation）
 */
export function useTriggerJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId) => apiClient.post(`/scheduler/trigger/${jobId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scheduler-status"] });
    },
  });
}

// ============================================================
// 统计概览 Hooks
// ============================================================

/**
 * 获取仪表盘统计数据（组合查询）
 */
export function useDashboardStats(queryOptions = {}) {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.get("/health"),
    ...queryOptions,
  });

  const unreadAlerts = useUnreadAlertCount({
    ...queryOptions,
  });

  const recentAnnouncements = useQuery({
    queryKey: ["opportunities", { page_size: 5 }],
    queryFn: () => apiClient.get("/announcements", { params: { page_size: 5 } }),
    ...queryOptions,
  });

  return {
    health: health.data,
    unreadAlerts: unreadAlerts.data,
    recentAnnouncements: recentAnnouncements.data?.items || [],
    isLoading: health.isLoading || unreadAlerts.isLoading || recentAnnouncements.isLoading,
    isError: health.isError || unreadAlerts.isError || recentAnnouncements.isError,
  };
}
