# 中国电信 & 中国联通采购平台 技术分析文档

> 文档版本: v1.0 | 最后更新: 2026-07-16

---

## 一、中国电信采购平台 (caigou.chinatelecom.com.cn) ✅ 已攻克

### 1.1 平台架构

| 项目 | 说明 |
|------|------|
| **前端框架** | Webpack + 自定义混淆器 |
| **页面类型** | SPA (Single Page Application) |
| **数据加载** | XHR/Fetch JSON API |
| **反爬等级** | ⭐ (低) — 实际防护弱于预期 |

### 1.2 真实 API 接口 ✅ 已确认

```
POST https://caigou.chinatelecom.com.cn/portal/base/announcementJoin/queryListNew
Content-Type: application/json;charset=UTF-8

请求体:
{
  "pageNum": 1,          // 页码
  "pageSize": 20,        // 每页条数
  "type": "xi9s",        // 公告类型编码: xi9s=采购公告, n0eves=结果公告
  "name": "广告"          // 可选: 搜索关键词
}

响应:
{
  "code": 200,
  "msg": "请求成功",
  "data": {
    "pageInfo": {
      "total": 101,           // 总条数
      "list": [...],          // 数据列表
      "pageNum": 1,
      "pageSize": 20,
      "hasNextPage": false    // ⚠️ 始终为 false, 需手动判断翻页
    }
  }
}
```

### 1.3 关键技术发现

| 项目 | 发现 |
|------|------|
| **是否需要签名** | ❌ 不需要！标准 JSON POST 即可 |
| **Cookie 验证** | 需要先 GET 首页获取 JSESSIONID 等 Cookie |
| **翻页机制** | hasNextPage 始终 false，通过 total 判断是否继续 |
| **搜索参数** | `name` 参数支持模糊搜索，但过于精确会漏数据 |
| **数据字段** | docTitle(标题), createDate(日期), docType(类型), provinceName(省份) |

### 1.4 验证结果

- ✅ 连续 10 次运行 100% 成功
- ✅ 每次获取 40 条数据（2种类型 × 2页 × 20条）
- ✅ 响应时间: 3-6 秒/请求
- ✅ 无 429 限流，无封禁

---

## 二、中国联通采购平台 (chinaunicombidding.cn) ✅ 已攻克

### 2.1 平台架构

| 项目 | 说明 |
|------|------|
| **前端框架** | UmiJS (React 企业级框架) |
| **UI 组件库** | Ant Design |
| **路由方式** | UmiJS 约定式路由 |
| **数据加载** | XHR/Fetch API |
| **反爬等级** | ⭐ (低) — 实际防护弱于预期 |

### 2.2 真实 API 接口 ✅ 已确认

```
POST https://www.chinaunicombidding.cn/api/v1/bizAnno/getAnnoList
Content-Type: application/json;charset=UTF-8

请求体:
{
  "pageNo": 1,                      // 页码
  "pageSize": 20,                   // 每页条数 (实际受限于服务端, 最多 ~10)
  "modeNo": "BizAnnoVoMtable",      // 数据源模式: Mtable=搜索, Btable=首页
  "annoName": "广告"                 // 搜索关键词 (服务端 LIKE 匹配)
}

响应 (Ant Design Pro 标准):
{
  "success": true,
  "total": 33,
  "data": [
    {
      "id": "2077645288254070784",
      "annoName": "2026年重庆联通广告宣传物料制作项目",
      "createDate": "2026-07-16 14:43:32",
      "annoType": "中标候选人公示",
      "provinceName": "重庆",
      "bidCompany": "中国联合网络通信有限公司重庆市分公司",
      "procurementType": "服务",
      "bidNo": "ND24102607000995"
    }
  ]
}
```

### 2.3 关键技术发现

| 项目 | 发现 |
|------|------|
| **Ym82oUM4 token** | 服务端自动处理，即使不传 token API 也正常返回 |
| **CORS 限制** | ❌ httpx 服务端请求完全不受 CORS 影响 |
| **搜索功能** | `annoName` 参数支持模糊匹配，效果很好 |
| **翻页机制** | 返回条数 < pageSize 时表示最后一页 |
| **数据质量** | 搜索"广告"精准命中 33 条真实广告类项目 |
| **字段映射** | annoName→标题, createDate→日期, annoType→类型, provinceName→省份 |

### 2.4 验证结果

- ✅ 连续运行均成功
- ✅ 每次获取 ~10 条（服务端限制每页最多10条）
- ✅ 搜索"广告"命中 33 条，100% 相关
- ✅ 响应时间: ~5 秒/请求
- ✅ 无 CORS 问题，无封禁

---

## 三、已发现问题和解决方案

### 3.1 问题清单

| # | 问题 | 平台 | 状态 | 解决方案 |
|---|------|------|------|----------|
| 1 | JS 高度混淆 | 电信 | ✅ 无需解决 | API 无签名，直接 httpx 调用 |
| 2 | Cookie 多层验证 | 电信 | ✅ 解决 | GET 首页获取 JSESSIONID 即可 |
| 3 | 请求参数签名 | 电信 | ✅ 无需解决 | 无签名机制 |
| 4 | CORS 跨域 | 联通 | ✅ 解决 | httpx 服务端请求不受限 |
| 5 | UmiJS 路由混淆 | 联通 | ✅ 解决 | Playwright 网络监控发现 API |
| 6 | Ym82oUM4 token | 联通 | ✅ 无需解决 | API 不校验 token |
| 7 | 翻页判断 | 电信 | ✅ 解决 | 通过 total/pageSize 计算 |
| 8 | 数据过滤 | 电信 | ⚠️ 需优化 | name 参数搜索面窄，建议无关键词采集后本地过滤 |

### 3.2 实际反爬等级评估（修正）

| 平台 | 预期难度 | 实际难度 | 说明 |
|------|---------|---------|------|
| 中国电信 | ⭐⭐⭐ | ⭐ | JS 混淆严重但 API 无签名 |
| 中国联通 | ⭐⭐ | ⭐ | CORS/Token 都不影响 httpx |

**核心发现**：两个平台的前端 JS 混淆都不影响后端 API 的可访问性。httpx 可以绕过所有前端防护。

---

## 四、测试数据格式

### 标准输出格式
```json
[
  {
    "title": "2026年广告宣传制作采购项目",
    "publish_date": "2026-07-15",
    "url": "https://caigou.chinatelecom.com.cn/...",
    "source": "caigou.chinatelecom.com.cn",
    "notice_type": "采购公告",
    "region": "广东"
  }
]
```

### 数据质量要求
- 标题：非空，长度 > 4
- 发布日期：格式 YYYY-MM-DD
- 链接：完整 URL
- 来源：标注平台名称
- 分类：正确识别广告类

---

## 五、后续集成计划

技术攻关完成后，在 `backend/adapters/` 中创建：
- `telecom_adapter.py` → 继承 `BaseAdapter`
- `unicom_adapter.py` → 继承 `BaseAdapter`
- 更新 `adapter_config.yaml`
