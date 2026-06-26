import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import AppLayout from "./layouts/AppLayout";
import OpportunityList from "./pages/OpportunityList";
import PurchaserProfile from "./pages/PurchaserProfile";
import RelationManagement from "./pages/RelationManagement";
import CityCompare from "./pages/CityCompare";
import Settings from "./pages/Settings";
import "./App.css";

function App() {
  return (
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
            <Route path="/" element={<Navigate to="/opportunities" replace />} />
            <Route path="/opportunities" element={<OpportunityList />} />
            <Route path="/purchaser-profile" element={<PurchaserProfile />} />
            <Route path="/client-relations" element={<RelationManagement />} />
            <Route path="/region-compare" element={<CityCompare />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
