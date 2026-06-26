# 📊 标中宝 - 广东移动招标情报系统 V1

> **版本**：V1.0.0  
> **定位**：专注于广东移动广告招标信息的收集、分析与筛选

---

## 🏗️ 技术架构

| 层级 | 技术栈 |
|------|--------|
| **后端** | Python 3.11 + FastAPI + SQLAlchemy (async) |
| **前端** | React 18 + Ant Design 5 |
| **数据库** | PostgreSQL 16 |
| **容器化** | Docker + Docker Compose |

---

## 📁 项目目录结构

```
bzb/
├── backend/                     # 后端代码
│   ├── app/
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── health.py    # 健康检查接口
│   │   ├── core/
│   │   │   └── config.py        # 应用配置
│   │   ├── db/
│   │   │   └── session.py       # 数据库会话管理
│   │   └── models/              # 数据模型
│   ├── requirements.txt         # Python 依赖
│   └── Dockerfile
├── frontend/                    # 前端代码
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.js               # 应用入口
│   │   ├── App.css              # 全局样式
│   │   ├── index.js             # ReactDOM 渲染
│   │   ├── layouts/
│   │   │   └── MainLayout.js    # 主布局（侧边栏+顶栏+内容区）
│   │   ├── pages/
│   │   │   └── Dashboard.js     # 数据看板页面
│   │   └── services/
│   │       └── api.js           # API 请求封装
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml           # 容器编排
└── README.md
```

---

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose
- Node.js 18+ (本地开发)
- Python 3.11+ (本地开发)

### 方式一：Docker Compose 一键启动（推荐）

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看运行状态
docker-compose ps

# 停止所有服务
docker-compose down
```

启动后访问：
- **前端页面**：http://localhost:3000
- **后端 API 文档**：http://localhost:8000/docs
- **健康检查**：http://localhost:8000/api/v1/health

### 方式二：本地开发

#### 1. 启动数据库

```bash
docker-compose up -d db
```

#### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. 启动前端

```bash
cd frontend
npm install
npm start
```

---

## 📡 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| GET | `/docs` | Swagger API 文档 |
| GET | `/redoc` | ReDoc API 文档 |

---

## 🗺️ 版本规划

- **V1.0** — 基础框架搭建，广东移动广告招标数据采集
- **V1.1** — 招标数据自动采集与入库
- **V1.2** — 情报分析与筛选功能
- **V2.0** — 扩展至更多行业与地区

---

## 👤 开发团队

标中宝项目组 © 2024
