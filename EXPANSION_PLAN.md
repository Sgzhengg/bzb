# 标中宝系统扩展技术规划

## 1. 项目目标

将系统从专注"广告类招标项目"扩展到政府采购网的**全品类招标项目**，包括：
- 设备采购
- 工程建设  
- 服务采购
- 以及原有的广告营销类

---

## 2. 当前系统架构分析

### 2.1 现有组件

| 组件 | 文件路径 | 当前功能 |
|------|----------|----------|
| **关键词过滤器** | `app/services/keyword_filter.py` | 仅识别广告类关键词 |
| **LLM分类器** | `app/services/llm_classifier.py` | 广告类判定+赛道分类 |
| **适配器基类** | `adapters/base_adapter.py` | 采集流程+广告过滤 |
| **ccgp适配器** | `adapters/ccgp_adapter.py` | 政府采购网采集 |
| **评分系统** | `app/api/v1/announcements.py` | 七维度机会评分 |
| **数据库** | `biaozhongbao.db` | announcements表 |

### 2.2 当前限制

1. **关键词过滤过于狭窄**：只识别广告相关关键词
2. **分类体系单一**：8个广告赛道，无法覆盖其他类型
3. **评分权重偏倚**：针对广告类项目优化
4. **数据字段固定**：缺少工程类、服务类的专用字段

---

## 3. 新分类体系设计

### 3.1 一级分类（6大类）

```python
PRIMARY_CATEGORIES = {
    "marketing": "广告营销类",      # 现有
    "equipment": "设备采购类",      # 新增
    "engineering": "工程建设类",    # 新增
    "service": "服务采购类",        # 新增
    "software": "软件信息化类",    # 新增
    "other": "其他类"              # 新增
}
```

### 3.2 二级分类（细分赛道）

```python
SECONDARY_CATEGORIES = {
    # 广告营销类（保留原有）
    "marketing": {
        "ad_design": "广告创意设计",
        "material_production": "物料制作印刷",
        "event_planning": "活动策划执行",
        "brand_promotion": "品牌宣传传播",
        "video_production": "视频内容制作",
        "new_media": "新媒体运营",
        "media_placement": "媒介资源投放",
        "channel_marketing": "渠道营销推广",
    },
    
    # 设备采购类（新增）
    "equipment": {
        "office_equipment": "办公设备",      # 电脑、打印机、投影仪等
        "communication": "通信设备",        # 电话、交换机、网络设备
        "special_equipment": "专业设备",    # 医疗、教学、科研设备
        "vehicle": "车辆采购",             # 公务车、特种车辆
        "security": "安防设备",            # 监控、门禁、报警系统
        "furniture": "家具用品",           # 办公家具、宿舍用品
    },
    
    # 工程建设类（新增）
    "engineering": {
        "construction": "建筑工程",        # 房建、市政工程
        "decoration": "装修工程",         # 室内装修、外立面改造
        "infrastructure": "基础设施",      # 道路、管网、绿化
        "weak_current": "弱电工程",       # 综合布线、监控系统
        "fire_fighting": "消防工程",      # 消防报警、喷淋系统
        "air_conditioning": "空调工程",   # 中央空调、通风系统
    },
    
    # 服务采购类（新增）
    "service": {
        "it_service": "IT服务",          # 系统集成、运维服务
        "consulting": "咨询服务",         # 管理咨询、技术咨询
        "training": "培训服务",          # 培训、会议服务
        "property_management": "物业管理",  # 保洁、安保、绿化
        "catering": "餐饮服务",          # 食堂承包、配餐服务
        "logistics": "物流服务",         # 快递、仓储、配送
        "maintenance": "维修服务",        # 设备维修、保养服务
    },
    
    # 软件信息化类（新增）
    "software": {
        "software_dev": "软件开发",      # 定制开发、系统集成
        "cloud_service": "云服务",        # IaaS、PaaS、SaaS
        "data_service": "数据服务",      # 大数据、人工智能服务
        "cybersecurity": "网络安全",    # 安全防护、风险评估
        "digital_transformation": "数字化转型",  # 数字化解决方案
    },
    
    # 其他类
    "other": {
        "supplies": "物资采购",          # 日用品、劳保用品
        "lease": "租赁服务",            # 设备租赁、场地租赁
        "insurance": "保险服务",         # 财产保险、人身保险
        "other": "其他"
    }
}
```

---

## 4. 组件扩展规划

### 4.1 关键词过滤器扩展

**文件**: `app/services/keyword_filter.py`

**修改内容**:
```python
# 新增设备类关键词
EQUIPMENT_KEYWORDS = [
    "办公设备", "电脑", "笔记本", "台式机", "打印机", "复印机",
    "投影仪", "显示屏", "通信设备", "交换机", "路由器",
    "服务器", "存储设备", "监控设备", "安防设备",
    "车辆采购", "公务车", "家具", "办公家具",
]

# 新增工程类关键词
ENGINEERING_KEYWORDS = [
    "建筑工程", "施工", "装修工程", "装饰工程",
    "市政工程", "基础设施", "道路建设", "管网工程",
    "弱电工程", "综合布线", "消防工程", "空调工程",
    "绿化工程", "景观工程",
]

# 新增服务类关键词
SERVICE_KEYWORDS = [
    "服务采购", "IT服务", "运维服务", "咨询服务",
    "培训服务", "会议服务", "物业管理", "保洁服务",
    "安保服务", "餐饮服务", "食堂承包", "物流服务",
    "维修服务", "保养服务",
]

# 新增软件类关键词
SOFTWARE_KEYWORDS = [
    "软件开发", "系统集成", "定制开发", "云服务",
    "大数据", "人工智能", "网络安全", "数字化",
    "信息化建设", "平台建设", "系统建设",
]
```

### 4.2 LLM分类器扩展

**文件**: `app/services/llm_classifier.py`

**修改内容**:
```python
# 扩展分类提示词
CATEGORIES = """
设备采购类：办公设备、通信设备、专业设备、车辆、安防、家具
工程建设类：建筑工程、装修工程、基础设施、弱电、消防、空调
服务采购类：IT服务、咨询、培训、物业、餐饮、物流、维修
软件信息化类：软件开发、系统集成、云服务、大数据、网络安全
广告营销类：广告设计、物料制作、活动策划、品牌传播、视频制作
"""

# 扩展字段提取
class AnnouncementExtraction(BaseModel):
    # 原有字段
    is_ad: bool
    category: Optional[str]
    
    # 新增字段
    primary_category: Optional[str]  # 一级分类
    secondary_category: Optional[str]  # 二级分类
    procurement_type: Optional[str]   # 采购类型：设备/工程/服务/软件
    quantity: Optional[float]         # 采购数量
    unit: Optional[str]               # 单位
    delivery_period: Optional[str]    # 交付周期
    qualification_requirements: Optional[str]  # 资质要求
```

### 4.3 数据库字段扩展

**文件**: 数据库迁移脚本

**新增字段**:
```sql
ALTER TABLE announcements ADD COLUMN primary_category VARCHAR(50);
ALTER TABLE announcements ADD COLUMN secondary_category VARCHAR(50);
ALTER TABLE announcements ADD COLUMN procurement_type VARCHAR(20);
ALTER TABLE announcements ADD COLUMN quantity REAL;
ALTER TABLE announcements ADD COLUMN unit VARCHAR(20);
ALTER TABLE announcements ADD COLUMN delivery_period VARCHAR(100);
ALTER TABLE announcements ADD COLUMN qualification_requirements TEXT;
ALTER TABLE announcements ADD COLUMN technical_requirements TEXT;
ALTER TABLE announcements ADD COLUMN business_requirements TEXT;

CREATE INDEX idx_primary_category ON announcements(primary_category);
CREATE INDEX idx_secondary_category ON announcements(secondary_category);
CREATE INDEX idx_procurement_type ON announcements(procurement_type);
```

### 4.4 适配器基类扩展

**文件**: `adapters/base_adapter.py`

**修改内容**:
```python
def _normalize_record(self, raw: Dict) -> Dict:
    # 扩展后的标准化映射
    return {
        # 原有字段
        "title": raw.get("title", ""),
        "purchaser": raw.get("purchaser", ""),
        "budget": raw.get("budget"),
        
        # 新增字段
        "primary_category": raw.get("primary_category", ""),
        "secondary_category": raw.get("secondary_category", ""),
        "procurement_type": raw.get("procurement_type", ""),
        "quantity": raw.get("quantity"),
        "unit": raw.get("unit"),
        "delivery_period": raw.get("delivery_period"),
        "qualification_requirements": raw.get("qualification_requirements", ""),
        
        # 保留is_ad字段用于向后兼容
        "is_ad": True,  # 扩展后所有项目都标记为机会
    }
```

### 4.5 评分系统扩展

**文件**: `app/api/v1/announcements.py`

**修改内容**:
```python
# 扩展评分维度（原7维度 → 9维度）
def _compute_announcement_score(ann: Announcement) -> dict:
    """
    九维度加权评分：
      1. 采购公平性 (15%) — 采购方式竞争程度
      2. 预算规模 (15%) — 预算金额
      3. 项目复杂度 (10%) — 技术难度评估
      4. 交付周期 (10%) — 时间压力
      5. 门槛友好度 (10%) — 资质要求严格度
      6. 在位者优势 (15%) — 历史中标情况
      7. 时效新鲜度 (10%) — 公告发布时间
      8. 信息完整度 (5%) — 信息披露完整度
      9. 地域便利性 (10%) — 项目所在地
    """
    
    # 根据primary_category调整权重
    category_weights = {
        "marketing": {"budget": 0.15, "complexity": 0.10},
        "equipment": {"budget": 0.20, "complexity": 0.05},
        "engineering": {"budget": 0.25, "complexity": 0.15},
        "service": {"budget": 0.10, "complexity": 0.10},
    }
```

---

## 5. 前端界面扩展

### 5.1 筛选器扩展

**文件**: `frontend/src/pages/OpportunityList.js`

**新增筛选选项**:
```jsx
// 分类筛选
<FormControl>
  <InputLabel>一级分类</InputLabel>
  <Select value={primaryCategory} onChange={handlePrimaryCategoryChange}>
    <MenuItem value="">全部</MenuItem>
    <MenuItem value="marketing">广告营销类</MenuItem>
    <MenuItem value="equipment">设备采购类</MenuItem>
    <MenuItem value="engineering">工程建设类</MenuItem>
    <MenuItem value="service">服务采购类</MenuItem>
    <MenuItem value="software">软件信息化类</MenuItem>
  </Select>
</FormControl>

// 采购类型筛选
<FormControl>
  <InputLabel>采购类型</InputLabel>
  <Select value={procurementType} onChange={handleProcurementTypeChange}>
    <MenuItem value="">全部</MenuItem>
    <MenuItem value="equipment">设备</MenuItem>
    <MenuItem value="engineering">工程</MenuItem>
    <MenuItem value="service">服务</MenuItem>
    <MenuItem value="software">软件</MenuItem>
  </Select>
</FormControl>
```

### 5.2 详情页扩展

**新增显示内容**:
- 采购类型标签
- 技术要求摘要
- 资质要求摘要
- 交付周期
- 数量与单位

---

## 6. 实施步骤

### 阶段1：后端扩展（1-2天）
1. ✅ 扩展关键词过滤器 (`keyword_filter.py`)
2. ✅ 更新LLM分类器 (`llm_classifier.py`)
3. ✅ 修改适配器基类 (`base_adapter.py`)
4. ✅ 更新ccgp适配器 (`ccgp_adapter.py`)
5. ✅ 数据库迁移

### 阶段2：评分系统调整（1天）
6. ✅ 扩展评分维度和权重
7. ✅ 根据分类调整评分算法

### 阶段3：前端界面更新（1-2天）
8. ✅ 更新筛选组件
9. ✅ 扩展详情页显示
10. ✅ 更新导出Excel模板

### 阶段4：测试与优化（1天）
11. ✅ 端到端测试
12. ✅ 性能优化
13. ✅ 用户文档更新

---

## 7. 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **分类准确度** | LLM可能误判分类 | 建立人工标注数据集，持续优化提示词 |
| **性能影响** | LLM调用增多导致变慢 | 批量处理+缓存机制 |
| **数据迁移** | 现有数据字段为空 | 设置默认值，渐进式填充 |
| **用户适应** | 界面变化大 | 保留原有视图，新增多维度视图 |

---

## 8. 成功指标

- 支持政府采购网全品类项目采集
- 分类准确率达到 85% 以上
- 评分系统覆盖所有新分类
- 用户体验平滑过渡

---

## 9. 技术要点

### 9.1 关键代码修改

**关键词过滤**：从"广告类判定"改为"全品类识别"
```python
def classify_project(title: str, content: str) -> Dict:
    """
    识别招标项目类型（6大类×N二级分类）
    返回: {primary_category, secondary_category, procurement_type, confidence}
    """
```

**LLM分类**：从"是否广告类"改为"分类+字段提取"
```python
def classify_and_extract(title: str, content: str) -> Dict:
    """
    一次性完成：
    1. 识别项目类型（6大类）
    2. 提取字段（预算、数量、资质等）
    3. 评估项目难度
    """
```

### 9.2 数据兼容性

- 保留 `is_ad` 字段用于向后兼容
- 现有广告类数据自动映射到新分类体系
- 前端同时支持新旧视图模式

---

## 10. 文件清单

### 需要修改的文件

| 文件 | 修改类型 | 优先级 |
|------|----------|--------|
| `app/services/keyword_filter.py` | 重构 | P0 |
| `app/services/llm_classifier.py` | 扩展 | P0 |
| `adapters/base_adapter.py` | 扩展 | P0 |
| `adapters/ccgp_adapter.py` | 优化 | P1 |
| `app/api/v1/announcements.py` | 扩展 | P1 |
| `frontend/src/pages/OpportunityList.js` | 扩展 | P1 |
| 数据库schema | 迁移 | P0 |

### 新增文件

| 文件 | 用途 |
|------|------|
| `backend/migrations/002_expand_categories.sql` | 数据库迁移 |
| `app/services/project_classifier.py` | 项目分类服务 |
| `app/services/scoring_engine.py` | 评分引擎（独立化）|

---

## 11. 测试用例

### 11.1 分类准确性测试

```python
def test_classification_accuracy():
    """测试分类准确度"""
    test_cases = [
        ("电脑设备采购", "equipment", "office_equipment"),
        ("办公楼装修工程", "engineering", "decoration"),
        ("软件开发服务", "software", "software_dev"),
        ("广告设计服务", "marketing", "ad_design"),
        ("物业管理服务", "service", "property_management"),
    ]
    
    for title, expected_primary, expected_secondary in test_cases:
        result = classify_project(title, "")
        assert result["primary_category"] == expected_primary
        assert result["secondary_category"] == expected_secondary
```

### 11.2 采集功能测试

```python
def test_ccgp_full_collection():
    """测试ccgp完整采集"""
    adapter = CcgpAdapter()
    results = adapter.run(max_pages=3, save_to_db=False)
    
    # 验证结果包含各种类型
    categories = set(r.get("primary_category") for r in results)
    assert len(categories) > 1  # 应有多种类型
```

---

## 12. 后续优化方向

1. **智能推荐**：基于用户历史偏好推荐项目
2. **价格分析**：同类项目价格趋势分析
3. **竞争分析**：各分类下的竞争态势
4. **自动文档生成**：根据项目类型生成投标文档模板

---

**规划版本**: v1.0  
**规划日期**: 2026-07-29  
**预计完成时间**: 3-5个工作日
