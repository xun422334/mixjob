import json as _json
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..config import DEEPSEEK_API_KEY
from ..models.database import get_db, Resume, ChatMessage, UserJobProfile
from ..services.ai_service import chat as ai_chat
from ..routes.cities import HOT_CITIES

router = APIRouter(prefix="/api/chat", tags=["chat"])

HOT_CITY_NAMES = {c["name"] for c in HOT_CITIES}

SYSTEM_PROMPT = """你是一个专业的职业规划助手。你的任务是：
1. 如果用户提供了简历信息，根据简历内容询问工作细节、项目经验、技术栈深度
2. 如果用户没有简历，主动引导用户描述工作经历、技能、期望岗位、期望薪资、期望城市
3. 对话友好简洁，每次只问1-2个问题
4. 如果你了解到用户对城市的偏好，要明确确认城市名

用户可能提供的简历信息将作为上下文提供给你。"""


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    resume_id: Optional[int] = None


@router.post("")
async def send_message(req: ChatRequest, db: Session = Depends(get_db)):
    if not DEEPSEEK_API_KEY:
        return {
            "response": "AI服务未配置API密钥，请在.env文件中设置DEEPSEEK_API_KEY。",
            "detected_cities": [],
        }

    # Get resume context
    resume_context = ""
    if req.resume_id:
        resume = db.query(Resume).filter(Resume.id == req.resume_id).first()
        if resume:
            resume_context = f"""
用户简历：
技能：{', '.join(resume.skills) if resume.skills else '未提供'}
工作经历：{_json.dumps(resume.experience, ensure_ascii=False) if resume.experience else '未提供'}
项目经历：{_json.dumps(resume.projects, ensure_ascii=False) if resume.projects else '未提供'}
教育背景：{_json.dumps(resume.education, ensure_ascii=False) if resume.education else '未提供'}
"""

    # Get chat history filtered by resume_id
    query = db.query(ChatMessage)
    if req.resume_id:
        query = query.filter(
            (ChatMessage.resume_id == req.resume_id) | (ChatMessage.resume_id.is_(None))
        )
    history = query.order_by(ChatMessage.created_at.asc()).all()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if resume_context:
        messages.append({"role": "system", "content": resume_context})
    for h in history[-20:]:
        role = "assistant" if h.role == "ai" else h.role
        messages.append({"role": role, "content": h.content})
    messages.append({"role": "user", "content": req.message})

    # Save user message
    db.add(ChatMessage(role="user", content=req.message, resume_id=req.resume_id))

    # Get AI response with better error handling
    try:
        ai_response = await ai_chat(messages)
    except Exception as e:
        error_str = str(e).lower()
        if "401" in error_str or "403" in error_str or "unauthorized" in error_str:
            print(f"[Chat] AI auth error: {e}")
            ai_response = "AI服务密钥无效，请检查DEEPSEEK_API_KEY是否正确配置。"
        elif "timeout" in error_str or "timed out" in error_str:
            print(f"[Chat] AI timeout: {e}")
            ai_response = "AI响应超时，请稍后重试。"
        else:
            print(f"[Chat] AI response failed: {e}")
            ai_response = "抱歉，我暂时无法回复，请稍后再试。"

    # Save AI response
    db.add(ChatMessage(role="ai", content=ai_response, resume_id=req.resume_id))
    db.commit()

    # Detect cities from the conversation
    detected_cities = detect_cities(req.message + " " + ai_response)

    # Extract desired position and salary via AI
    detected_position = ""
    detected_salary = ""
    try:
        extract_prompt = f"""从用户最新消息中提取期望岗位和期望薪资。
用户消息：{req.message}
AI回复（仅供上下文）：{ai_response[:200]}

规则：
1. 如果用户明确提到期望岗位（如"我想找产品经理"、"目标岗位是开发"），提取出来
2. 如果用户提到期望薪资（如"15k"、"1.5万"、"20-30万"），提取出来
3. 没有就返回空字符串
4. 返回纯JSON：{{"position": "岗位", "salary": "薪资"}}
只返回JSON。"""
        result = await ai_chat([
            {"role": "system", "content": "你是一个信息提取助手，只返回JSON。"},
            {"role": "user", "content": extract_prompt},
        ])
        extracted = _json.loads(result.strip())
        detected_position = extracted.get("position", "").strip()
        detected_salary = extracted.get("salary", "").strip()
    except Exception:
        pass

    # Update user profile with detected info
    profile = db.query(UserJobProfile).first()
    if not profile:
        profile = UserJobProfile()
        db.add(profile)
    if detected_cities:
        existing = set(profile.desired_cities or [])
        for c in detected_cities:
            existing.add(c)
        profile.desired_cities = list(existing)
    if detected_position and not profile.desired_position:
        profile.desired_position = detected_position
    if detected_salary and not profile.desired_salary:
        profile.desired_salary = detected_salary
    db.commit()

    return {
        "response": ai_response,
        "detected_cities": detected_cities,
        "detected_position": detected_position,
    }


@router.get("/profile")
async def get_profile(db: Session = Depends(get_db)):
    profile = db.query(UserJobProfile).first()
    if not profile:
        return {"desired_cities": [], "desired_position": "", "desired_salary": ""}
    return {
        "desired_cities": profile.desired_cities or [],
        "desired_position": profile.desired_position or "",
        "desired_salary": profile.desired_salary or "",
    }


@router.get("/history")
async def get_history(resume_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(ChatMessage)
    if resume_id:
        query = query.filter(
            (ChatMessage.resume_id == resume_id) | (ChatMessage.resume_id.is_(None))
        )
    messages = query.order_by(ChatMessage.created_at.asc()).all()
    return {
        "messages": [{"role": m.role, "content": m.content} for m in messages]
    }


@router.get("/keywords")
async def get_chat_keywords(db: Session = Depends(get_db)):
    """Generate search keywords from chat history and user profile using AI."""
    if not DEEPSEEK_API_KEY:
        return {"keywords": ""}

    profile = db.query(UserJobProfile).first()
    desired_position = profile.desired_position if profile else ""

    # Get recent chat messages (without resume_id filter)
    recent = db.query(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(30).all()
    recent.reverse()

    conversation = "\n".join([
        f"{'用户' if m.role == 'user' else 'AI'}: {m.content[:200]}"
        for m in recent[-20:]
    ])

    if not conversation and not desired_position:
        return {"keywords": ""}

    try:
        prompt = f"""根据以下对话历史，生成5-8个适合在招聘网站搜索岗位的关键词。

对话历史：
{conversation if conversation else '无对话'}

用户期望岗位：{desired_position or '未明确'}

规则：
1. 从对话中提取用户提到的职位意向、技能对应的职位、感兴趣的岗位
2. 关键词必须是具体的职位名称，例如"Python开发工程师"而非"Python"，"数据分析师"而非"数据分析"
3. 优先提取用户明确表达过兴趣的岗位方向
4. 关键词用 / 分隔
5. 返回纯JSON：{{"keywords": "关键词1/关键词2/关键词3"}}

只返回JSON，不要其他内容。"""

        response = await ai_chat([
            {"role": "system", "content": "你是一个招聘搜索专家，精通招聘网站的搜索机制。你必须从对话中提取具体的职位名称作为关键词。只返回JSON。"},
            {"role": "user", "content": prompt},
        ])

        result = _json.loads(response.strip())
        keywords = result.get("keywords", "")
    except Exception as e:
        print(f"[Chat] keywords generation failed: {e}")
        keywords = ""

    return {"keywords": keywords}


def detect_cities(text: str) -> list[str]:
    found = []
    for city in HOT_CITY_NAMES:
        if city in text:
            found.append(city)
    return found
