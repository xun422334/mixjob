# 技术规格 - AI智能求职匹配平台

## 技术栈

| 层 | 技术 | 版本 |
|---|---|---|
| 前端框架 | React + Vite | 18+ |
| 前端语言 | TypeScript | 5.x |
| CSS框架 | Tailwind CSS | 3.x |
| 后端框架 | Python FastAPI | 0.100+ |
| ORM | SQLAlchemy | 2.x |
| 数据库 | SQLite | 3.x |
| AI模型 | DeepSeek API (deepseek-chat) | latest |
| 文件解析 | PyPDF2 + python-docx | latest |
| HTTP抓取 | requests + beautifulsoup4 | latest |

## 后端API设计

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/resume/upload | 上传简历文件 |
| GET | /api/resume/{id} | 获取简历解析结果 |
| POST | /api/chat | 发送对话消息 |
| GET | /api/chat/history | 获取对话历史 |
| GET | /api/cities | 获取城市列表 |
| POST | /api/jobs | 手动添加岗位 |
| GET | /api/jobs | 查询岗位列表（?city=&keyword=） |
| GET | /api/match | 匹配推荐（?city=&min_score=70） |
| POST | /api/resume/update | 根据岗位生成优化简历 |

## 数据库表

- **users**: id, created_at
- **resumes**: id, user_id, filename, raw_text, skills, experience, education, created_at
- **chat_messages**: id, user_id, role, content, created_at
- **job_listings**: id, title, company, description, requirements, source, source_url, salary, city, location, created_at
- **match_results**: id, resume_id, job_id, score, is_recommended, created_at
- **user_job_profiles**: id, user_id, desired_position, desired_salary, desired_cities, skills_extra

## 前端路由

| 路径 | 页面 | 说明 |
|---|---|---|
| / | HomePage | 主页（左侧上传+对话，右侧推荐列表） |

## 环境变量

```
DEEPSEEK_API_KEY=sk-xxx    # DeepSeek API密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DATABASE_URL=sqlite:///./job.db
```
