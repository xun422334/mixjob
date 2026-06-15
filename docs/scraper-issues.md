# 爬虫问题诊断报告

> 生成日期：2026-06-15
> 诊断范围：BOSS直聘、猎聘、国聘 三个爬虫返回空数据的原因

---

## 根本原因

**三个平台均为 JavaScript SPA（单页应用），职位列表通过 JS 动态渲染。当前使用 httpx（纯 HTTP 客户端）只能获取空 HTML 骨架，不含任何职位数据。**

详情页抓取（`backend/app/routes/jobs.py` 中的 `_fetch_detail_page`）使用 Playwright 带 JS 渲染是正确的，但列表抓取（`backend/app/services/scrapers/*.py`）错误地使用了 httpx。

---

## 一、BOSS直聘

| # | 问题 | 严重度 | 位置 |
|---|------|--------|------|
| 1 | **使用 httpx 抓取 React SPA 页面** — 无 JS 渲染，获取不到任何职位列表 | 致命 | [boss.py:44-50](../backend/app/services/scrapers/boss.py#L44-L50) |
| 2 | **搜索 URL 拼写错误** — `/web/geek/jobs` 应为 `/web/geek/job`（单数） | 致命 | [boss.py:28](../backend/app/services/scrapers/boss.py#L28) |
| 3 | **Cookie 已过期** — 状态文件保存于 6月3日，距今超过 24h 过期阈值 | 致命 | [boss.py:30-31](../backend/app/services/scrapers/boss.py#L30-L31) |
| 4 | **反爬虫令牌** — `__zp_stoken__` 需要在 JS 执行上下文中动态协商，httpx 无法处理 | 高 | - |
| 5 | **CSS 选择器为猜测值** — `.job-name`, `.boss-name` 等选择器未经实际页面验证 | 中 | [boss.py:60-74](../backend/app/services/scrapers/boss.py#L60-L74) |
| 6 | **`print()` 调试语句残留** — 应使用 logger | 低 | [boss.py:51,61](../backend/app/services/scrapers/boss.py#L51) |

### 修复方向

- 改用 Playwright 加载 `browser_states/boss_state.json` 作为 storage_state
- 等待 `networkidle` 后再解析 DOM
- 修正搜索 URL 为 `/web/geek/job?query=...&city=...`
- 用户需重新登录以刷新 Cookie

---

## 二、猎聘

| # | 问题 | 严重度 | 位置 |
|---|------|--------|------|
| 1 | **使用 httpx 抓取 JS 渲染页面** — 职位列表完全由 AJAX 动态加载 | 致命 | [liepin.py:29-34](../backend/app/services/scrapers/liepin.py#L29-L34) |
| 2 | **完全不加载 Cookie** — `browser_states/liepin_state.json` 存在但未读取，以匿名用户身份请求 | 致命 | [liepin.py](../backend/app/services/scrapers/liepin.py) |
| 3 | **阿里云 WAF 拦截** — Cookie 中含有 `acw_tc` 令牌，无 Cookie 请求会被 WAF 拦截返回验证码页面 | 高 | - |
| 4 | **CSS 选择器过于宽泛** — `[class*='job-list-item']` 等选择器依赖猜测的类名 | 中 | [liepin.py:41-47](../backend/app/services/scrapers/liepin.py#L41-L47) |
| 5 | **`print()` 调试语句残留** | 低 | [liepin.py:35,48](../backend/app/services/scrapers/liepin.py#L35) |

### 修复方向

- 改用 Playwright 加载 `browser_states/liepin_state.json`
- 猎聘反爬较强（阿里云 WAF），可能需要额外等待和 human-like 行为模拟
- 使用更精确的选择器定位职位卡片

---

## 三、国聘

| # | 问题 | 严重度 | 位置 |
|---|------|--------|------|
| 1 | **使用 httpx 抓取 JS 渲染页面** | 致命 | [guopin.py:22-27](../backend/app/services/scrapers/guopin.py#L22-L27) |
| 2 | **搜索 URL 未传入城市参数** — `self.city` 从未用于 URL 构造 | 高 | [guopin.py:16](../backend/app/services/scrapers/guopin.py#L16) |
| 3 | **CSS 选择器 `[class*='card']` 过于宽泛** — 匹配任意含 "card" class 的元素（Bootstrap 卡片、模态框等） | 高 | [guopin.py:34](../backend/app/services/scrapers/guopin.py#L34) |
| 4 | **解析逻辑全为启发式猜测** — `lines[0]` 当标题、关键词匹配找公司名等，误判率极高 | 高 | [guopin.py:43-78](../backend/app/services/scrapers/guopin.py#L43-L78) |
| 5 | **`print()` 调试语句残留** | 低 | [guopin.py:28,35](../backend/app/services/scrapers/guopin.py#L28) |

### 修复方向

- 改用 Playwright 渲染页面
- 添加城市参数到搜索 URL：`/job?keyword=xxx&city=xxx`
- 使用国聘实际 DOM 结构的选择器
- 重写解析逻辑，基于结构化 DOM 而非文本启发式

---

## 四、全局问题

| # | 问题 | 位置 |
|---|------|------|
| 1 | **`rate_limit_delay` 定义但从未使用** — 所有爬虫都定义了 `rate_limit_delay = 2.0`，但 `job_scraper.py` 传 `delay=0` | [job_scraper.py:29](../backend/app/services/job_scraper.py#L29) |
| 2 | **无任何爬虫单元测试** | - |
| 3 | **超时设置偏短** — 从 30s 降到 20s，Playwright 渲染页面可能需要更长时间 | [job_scraper.py:106](../backend/app/services/job_scraper.py#L106) |
| 4 | **智联招聘同样使用 httpx** — 虽然本次不在排查范围，但存在相同问题 | [zhaopin.py:22-27](../backend/app/services/scrapers/zhaopin.py#L22-L27) |

---

## 五、架构建议

1. **统一使用 Playwright** — 详情页抓取已用 Playwright，列表抓取也应统一
2. **提取公共 Playwright 工具函数** — 创建 browser context、加载 storage_state、等待渲染的逻辑复用
3. **Cookie 有效期管理** — 当前 24h 过期阈值合理，但需要在抓取前主动检查并提示用户重新登录
4. **添加测试** — 至少对解析逻辑添加单元测试，使用保存的 HTML 快照作为 fixture
