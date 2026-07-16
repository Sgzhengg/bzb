# 标中宝 — 电信/联通平台独立技术攻关

## 📋 项目概述

本目录包含中国电信和中国联通采购平台的独立技术攻关脚本。这些脚本完全独立于主项目，专注于攻克反爬虫技术难题。

## 🏗️ 目录结构

```
telecom_unicom_breaker/
├── telecom_breaker.py      # 中国电信平台攻关脚本
├── unicom_breaker.py       # 中国联通平台攻关脚本
├── requirements.txt        # Python 依赖
├── README.md               # 本文档
├── TECH_ANALYSIS.md        # 技术分析文档
├── logs/                   # 运行日志
└── output/                 # 输出数据和分析结果
```

## 🚀 快速开始

### 1. 环境准备

```bash
cd telecom_unicom_breaker

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 2. 中国电信平台攻关

```bash
# Step 1: 浏览器网络分析（找到真实 API）
# 不加 --headless 可以看到浏览器操作过程
python telecom_breaker.py --mode analyze

# 如果服务器在远程，使用无头模式
python telecom_breaker.py --mode analyze --headless

# Step 2: 数据采集（基于分析结果）
python telecom_breaker.py --mode collect --keyword "广告"

# Step 3: 验证测试（连续 10 次）
python telecom_breaker.py --mode validate

# Step 4: 全流程自动化
python telecom_breaker.py --mode all
```

### 3. 中国联通平台攻关

```bash
# Step 1: 浏览器网络分析
python unicom_breaker.py --mode analyze

# Step 2: CORS 绕过测试
python unicom_breaker.py --mode cors-test

# Step 3: 数据采集
python unicom_breaker.py --mode collect --keyword "广告"

# Step 4: 验证测试
python unicom_breaker.py --mode validate

# Step 5: 全流程
python unicom_breaker.py --mode all
```

## 🔍 技术攻关策略

### 中国电信平台 (caigou.chinatelecom.com.cn)

| 挑战 | 难度 | 策略 |
|------|------|------|
| JavaScript 混淆 | ⭐⭐⭐ | Playwright 浏览器监控网络请求，不逆向 JS |
| 多层 Cookie 验证 | ⭐⭐⭐ | 浏览器自动处理 Cookie，监控刷新时机 |
| 请求参数签名 | ⭐⭐⭐ | 用浏览器发起请求，捕获完整请求参数 |
| 频率限制 | ⭐⭐ | 随机延迟 + 指数退避 |

**核心思路**：避重就轻——不逆向 JS，而是用浏览器"录制"API 调用，然后用 httpx 复现。

### 中国联通平台 (chinaunicombidding.cn)

| 挑战 | 难度 | 策略 |
|------|------|------|
| UmiJS 路由混淆 | ⭐⭐ | 监控 XHR/Fetch 请求，提取真实 API 路径 |
| CORS 跨域限制 | ⭐⭐ | httpx 不经过浏览器，不受 CORS 限制 |
| X-Frame-Options | ⭐ | Playwright route 拦截移除限制头 |
| JS 混淆 ($_ts) | ⭐⭐⭐ | 不逆向，直接监控网络请求 |

**核心思路**：httpx 服务端请求绕过 CORS，Playwright 路由拦截绕过 X-Frame-Options。

## 📊 脚本模式说明

### analyze 模式
- 启动 Playwright 浏览器
- 监控所有 XHR/Fetch 请求
- 自动尝试搜索和翻页
- 保存 API 分析结果到 JSON

### collect 模式
- Strategy A: 使用分析出的 API 直接调用（httpx）
- Strategy B: Playwright 页面级 HTML 解析（兜底）
- 自动过滤广告类项目
- 保存结构化数据

### validate 模式
- 连续采集 10 次
- 统计成功率
- 验证数据完整性

## 🎯 成功标准

- [ ] 独立脚本可稳定获取数据
- [ ] API 接口和参数明确
- [ ] 反爬虫机制有效应对
- [ ] 连续 10 次运行无失败
- [ ] 数据包含标题、日期、链接等核心字段
- [ ] 正确识别广告类项目

## ⚠️ 注意事项

1. **独立性原则**：这些脚本完全独立，不依赖主项目代码
2. **稳定性优先**：宁可慢但稳定，不要快但不稳定
3. **频率限制**：严格遵守访问频率，默认延迟 3-6 秒
4. **法律合规**：仅用于商业情报采集，遵守 robots.txt
