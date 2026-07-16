import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ConfigProvider, App as AntApp, theme } from "antd";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import zhCN from "antd/locale/zh_CN";
import AppLayout from "./layouts/AppLayout";
import OpportunityList from "./pages/OpportunityList";
import AnnouncementDetail from "./pages/AnnouncementDetail";
import RelationManagement from "./pages/RelationManagement";
import Settings from "./pages/Settings";
import WinningResults from "./pages/WinningResults";
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
        <AntApp>
          <BrowserRouter
            future={{
              v7_startTransition: true,
              v7_relativeSplatPath: true,
            }}
          >
            <Routes>
              <Route element={<AppLayout />}>
                <Route path="/" element={<OpportunityList />} />
                <Route path="/opportunities" element={<OpportunityList />} />
                <Route path="/opportunities/:id" element={<AnnouncementDetail />} />
                <Route path="/client-relations" element={<RelationManagement />} />
                <Route path="/winning-results" element={<WinningResults />} />
                <Route path="/settings" element={<Settings />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;
