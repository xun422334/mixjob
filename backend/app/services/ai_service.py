import json
import httpx
from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL


async def chat(messages: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[AI] chat API call failed: {e}")
            raise


async def match_score(resume_info: dict, job_info: dict) -> dict:
    prompt = f"""你是一个专业的招聘匹配评估专家。请根据候选人的简历和岗位要求，评估匹配度。

候选人信息：
- 技能：{', '.join(resume_info.get('skills', []))}
- 工作经历：{json.dumps(resume_info.get('experience', []), ensure_ascii=False)}
- 项目经历：{json.dumps(resume_info.get('projects', []), ensure_ascii=False)}
- 教育背景：{json.dumps(resume_info.get('education', []), ensure_ascii=False)}

岗位信息：
- 职位：{job_info.get('title', '')}
- 公司：{job_info.get('company', '')}
- 描述：{job_info.get('description', '')}
- 要求：{job_info.get('requirements', '')}

请给出0到100的匹配度分数，返回纯JSON：
{{"score": 85, "reason": "一句话简述匹配理由（中文，不超过30字）"}}

只返回JSON，不要其他内容。"""

    response = await chat([
        {"role": "system", "content": "你是一个招聘匹配评估专家，只返回JSON。"},
        {"role": "user", "content": prompt},
    ])

    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            print(f"[AI] match_score JSON parse failed: {e}, raw: {response[:200]}")
            return {"score": 0, "reason": "AI评分服务暂不可用"}


async def update_resume(resume_info: dict, job_info: dict) -> str:
    personal = resume_info.get('personal_info', {}) or {}
    prompt = f"""你是一个专业的简历优化专家。请根据目标岗位的要求，优化候选人的简历，使其更具针对性和竞争力。

候选人原始简历信息：
- 个人信息：姓名={personal.get('name', '')}、电话={personal.get('phone', '')}、邮箱={personal.get('email', '')}
- 获奖荣誉：{', '.join(personal.get('awards', [])) if personal.get('awards') else '无'}
- 证书资质：{', '.join(personal.get('certs', [])) if personal.get('certs') else '无'}
- 技能：{', '.join(resume_info.get('skills', []))}
- 工作经历：{json.dumps(resume_info.get('experience', []), ensure_ascii=False)}
- 项目经历：{json.dumps(resume_info.get('projects', []), ensure_ascii=False)}
- 教育背景：{json.dumps(resume_info.get('education', []), ensure_ascii=False)}

目标岗位：
- 职位：{job_info.get('title', '')}
- 公司：{job_info.get('company', '')}
- 岗位描述：{job_info.get('description', '')}
- 任职要求：{job_info.get('requirements', '')}

请生成一份针对该岗位的优化简历，包含以下部分：

1. **个人信息**：必须保留原始信息 — 姓名={personal.get('name', '')}、电话={personal.get('phone', '')}、邮箱={personal.get('email', '')}
2. **技能清单**（将与岗位要求匹配的技能放在前面，标注熟练程度）
3. **工作经历**（针对岗位要求重写描述，突出相关项目经验和成果，使用数据量化）
4. **项目经历**（保留与岗位匹配的重要项目，用STAR法则描述）
5. **教育背景**
6. **获奖与证书**（保留原始获奖和证书）
7. **自我评价**（2-3句话，突出与该岗位的匹配度）

要求：
- 内容必须基于候选人真实经历，不编造
- **必须**保留原始个人信息（姓名、电话、邮箱），不可省略
- 保留全部获奖荣誉和证书资质
- 语言专业简洁，使用STAR法则描述经历
- 突出与岗位要求的匹配点"""

    response = await chat([
        {"role": "system", "content": "你是一个专业简历优化师，帮助求职者针对特定岗位优化简历。"},
        {"role": "user", "content": prompt},
    ])
    return response


async def structure_resume(raw_text: str) -> dict:
    prompt = """你是一个专业简历解析助手。请从以下简历文本中提取**全部**信息，不要遗漏任何内容。返回纯JSON格式（不要包含```json标记）。

重要：请区分"工作经历"和"项目经历"：
- **工作经历 (work_experience)**：在公司/组织的正式任职经历
- **项目经历 (project_experience)**：参与的具体项目，可能是工作中的项目或独立项目

{
  "skills": ["技能名称"],
  "work_experience": [
    {"company": "公司名称", "position": "职位", "duration": "起止时间", "description": "工作职责和成果"}
  ],
  "project_experience": [
    {"name": "项目名称", "role": "担任角色", "duration": "项目周期", "description": "项目内容和成果", "tech_stack": ["使用技术"]}
  ],
  "education": [
    {"school": "学校名称", "degree": "学历", "major": "专业", "year": "毕业年份"}
  ],
  "personal_info": {
    "name": "姓名",
    "phone": "手机号",
    "email": "邮箱",
    "awards": ["获奖荣誉"],
    "certs": ["证书资质"]
  }
}

注意：
1. 提取简历中的**全部**内容，不要省略任何技能、经历或教育背景
2. 如果某项信息没有找到，填写空字符串或空数组[]
3. 个人信息中的awards和certs如果在简历中没有，返回空数组
4. 只返回JSON，不要有其他文字

简历文本：
""" + raw_text

    response = await chat([
        {"role": "system", "content": "你是一个简历解析助手，只返回JSON，不要有其他内容。"},
        {"role": "user", "content": prompt},
    ])

    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            print(f"[AI] JSON parse failed: {e}, raw: {response[:200]}")
            return {}
