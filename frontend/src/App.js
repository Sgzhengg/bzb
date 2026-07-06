import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, theme } from "antd";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import zhCN from "antd/locale/zh_CN";
import AppLayout from "./layouts/AppLayout";
import Dashboard from "./pages/Dashboard";
import OpportunityList from "./pages/OpportunityList";
import AnnouncementDetail from "./pages/AnnouncementDetail";
import PurchaserProfile from "./pages/PurchaserProfile";
import RelationManagement from "./pages/RelationManagement";
import CityCompare from "./pages/CityCompare";
import Settings from "./pages/Settings";
import "./App.css";

// 创建 React Query 客户端
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 数据保持新鲜 5 分钟
      staleTime: 5 * 60 * 1000,
      // 缓存时间 10 分钟
      gcTime: 10 * 60 * 1000,
      // 失败时重试 1 次
      retry: 1,
      // 窗口焦点变化时自动重新获取（可关闭）
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          algorithm: theme.defaultAlgorithm,
          token: { colorPrimary: "#1677ff", borderRadius: 6 },
        }}
      >
        <BrowserRouter>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/opportunities" element={<OpportunityList />} />
              <Route path="/opportunities/:id" element={<AnnouncementDetail />} />
              <Route path="/purchaser-profile" element={<PurchaserProfile />} />
              <Route path="/client-relations" element={<RelationManagement />} />
              <Route path="/region-compare" element={<CityCompare />} />
              <Route path="/settings" element={<Settings />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;
