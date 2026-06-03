# CLAUDE.md - AI智能求职匹配平台

## 项目概述
这是一个AI驱动的求职匹配平台，帮助用户上传简历、与AI对话挖掘职业背景，然后从多个招聘渠道按城市抓取岗位并进行智能匹配推荐。

## 关键文件路径

| 文件 | 路径 | 说明 |
|---|---|---|
| 需求文档 | [docs/requirements.md](docs/requirements.md) | 功能和非功能需求 |
| 技术规格 | [docs/tech-spec.md](docs/tech-spec.md) | 技术栈、API设计、数据模型 |
| 设计规范 | [docs/design.md](docs/design.md) | 颜色、组件、响应式、布局 |
| 执行步骤 | [docs/execution-plan.md](docs/execution-plan.md) | 分阶段执行计划 |
| 开发日志 | [devlog/](devlog/) | 每天开发记录 |

## 工作指引

### 开发节奏
- 严格按照 [docs/execution-plan.md](docs/execution-plan.md) 中的阶段顺序执行
- 每阶段完成后验证功能正常，再进入下一阶段
- 不要一次性做太多，保持增量开发

### 开发习惯
- 每阶段先写后端API，再写前端组件
- 先保证功能可用，再优化样式细节
- 完成后更新 devlog/ 下的当天日志

### 技术栈
- 前端：React 18 + Vite + TypeScript + Tailwind CSS
- 后端：Python FastAPI + SQLAlchemy + SQLite
- AI：DeepSeek API
- 文件解析：PyPDF2 + python-docx

### 颜色主题（浅蓝色）
- 页面背景 `#F5F9FF`，主色 `#42A5F5`，卡片 `#BBDEFB`，深蓝文字 `#1E88E5`

### 用户偏好
- 用户是不懂代码的小白，操作要简单直观
- 所有页面需要电脑和手机端都能用（响应式）
- 只展示匹配度≥70%的岗位，不要随意推荐
- 招聘岗位需标注来源
