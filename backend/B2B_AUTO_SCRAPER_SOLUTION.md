# b2b SPA 自动导航解决方案

## 🎯 问题分析

你面临的核心问题是：
1. **b2b.10086.cn 是复杂的 Vue SPA** - 直接访问 hash 路由会 404
2. **Vue Router 导航失败** - 现有的 JS 代码无法触发路由
3. **模拟点击无效** - DOM 元素没有正确绑定事件
4. **SSL 问题** - Playwright 的网络请求与 httpx 不同栈

## 🔧 已实施的解决方案

### 1. 多重导航策略

我为你实施了以下改进：

#### 策略 A：真实用户点击模拟
- 填入搜索关键词到搜索框
- 按 Enter 触发搜索
- 查找包含目标标题的表格行
- 尝试多种点击方式（链接、行点击）

#### 策略 B：增强的 Vue Router 导航
- Vue 3 全局路由器访问
- Vue 2 兼容性支持
- Window 全局对象路由器
- 手动 hash 变化 + 事件触发

#### 策略 C：可靠的详情页检测
- 三重检测机制：
  - URL 变化检测（包含 "detail"）
  - 文本长度显著增加（>3000 字符）
  - DOM 元素变化检测

### 2. 核心改进文件

**`backend/app/services/b2b_auto_scraper.py`**
- 实现了完整的用户行为模拟
- 添加了多重导航策略
- 改进了详情页检测机制
- 提供了详细的成功/失败日志

**`backend/app/api/v1/announcements.py`**
- 已配置使用自动刮削器
- 添加了方法追踪信息
- 改进了错误处理

**`backend/test_b2b_auto.py`** (新增)
- 独立测试脚本
- 支持多个关键词测试
- 详细的执行日志

## 🧪 测试方法

### 方法 1：独立测试脚本

```bash
cd backend
python test_b2b_auto.py
```

### 方法 2：通过 API 测试

```bash
# 启动后端
cd backend
python run.py

# 调用 API
curl -X POST "http://localhost:8000/api/v1/announcements/extract-budget/batch?limit=1"
```

### 方法 3：前端界面测试

1. 启动前端和后端
2. 在"机会列表"页面点击"刷新预算"按钮
3. 观察 Edge 浏览器自动操作

## 🔍 关键改进点

### 1. 真实用户行为模拟
```python
# 不再只是注入结果，而是真实模拟用户操作
search_input.fill(keyword[:30])
search_input.press("Enter")
page.wait_for_timeout(3000)  # 等搜索结果加载
```

### 2. 智能表格行查找
```python
# 查找包含目标标题的行
const text = row.innerText.toLowerCase();
if (text.includes(targetTitle) && text.length > 20) {
    // 找到匹配的行，执行点击
    link.click() or row.click()
}
```

### 3. 增强的 Vue Router 访问
```python
# 尝试多种 Vue 版本的路由器访问方式
if (app.__vue_app__) { /* Vue 3 */ }
if (app.__vue__) { /* Vue 2 */ }
if (window.$router) { /* Window 全局 */ }
```

### 4. 可靠的详情页检测
```python
# 多重检测机制确保准确性
if "detail" in current_url.lower() or len(page_text) > 3000:
    detail_detected = True
```

## 🎯 预期结果

### 成功情况
- ✅ Edge 浏览器自动打开
- ✅ 搜索词自动填入
- ✅ 搜索结果自动点击
- ✅ 详情页自动加载
- ✅ 正文内容自动提取
- ✅ LLM 预算提取正常工作

### 失败情况
- ⚠️ 如果策略 A（点击）失败，自动尝试策略 B（Vue Router）
- ⚠️ 如果策略 B 也失败，返回 `null` 并记录详细日志
- ⚠️ 可以回退到原始的手动模式（b2b_scraper.py）

## 🛠️ 进一步调试建议

如果自动导航仍然失败，可以：

1. **增加日志详细程度**
```python
logging.basicConfig(level=logging.DEBUG)
```

2. **手动分析 b2b SPA**
- 打开 Edge 开发者工具
- 查看 Console 中的 Vue 对象
- 分析网络请求的顺序

3. **使用 headed 模式观察**
```python
browser = pw.chromium.launch(headless=False, channel="msedge", slow_mo=1000)
```

4. **检查特定的 DOM 结构**
```python
# 在 evaluate 中添加调试信息
console.log('Table found:', tables.length);
console.log('Rows found:', rows.length);
```

## 📋 技术栈总结

- **Playwright 同步 API** - 浏览器自动化
- **httpx + 自定义 SSL Context** - 解决 b2b SSL 问题
- **Vue Router 编程导航** - SPA 路由控制
- **多重回退策略** - 确保高成功率
- **三重检测机制** - 可靠的状态检测

现在你可以运行测试，看看改进后的自动刮削器是否能成功解决 b2b SPA 导航问题！