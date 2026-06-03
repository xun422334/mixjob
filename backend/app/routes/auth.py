import os
import subprocess
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/auth", tags=["auth"])

BROWSER_STATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "browser_states"
)

LOGIN_URLS = {
    "boss": "https://www.zhipin.com/web/user/?ka=header-login",
    "liepin": "https://www.liepin.com/login/",
    "zhaopin": "https://passport.zhaopin.com/login",
    "guopin": "https://www.iguopin.com/login",
}

SITE_NAMES = {
    "boss": "BOSS直聘",
    "liepin": "猎聘",
    "zhaopin": "智联招聘",
    "guopin": "国聘",
}


@router.post("/login/{source}")
async def login_source(source: str):
    """Launch Playwright browser for user to log in"""
    if source not in LOGIN_URLS:
        raise HTTPException(status_code=400, detail=f"不支持的来源: {source}")

    os.makedirs(BROWSER_STATE_DIR, exist_ok=True)

    script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "login_helper.py"
    )

    try:
        subprocess.Popen(
            ["python3", script, source],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动登录浏览器失败: {str(e)}")

    return {
        "status": "browser_opened",
        "message": f"已打开{SITE_NAMES.get(source, source)}登录页面，请在浏览器中完成登录",
        "login_url": LOGIN_URLS[source],
    }


@router.get("/login/status/{source}")
async def login_status(source: str):
    """Check if user is logged in to a recruitment site"""
    state_file = os.path.join(BROWSER_STATE_DIR, f"{source}_state.json")

    if not os.path.exists(state_file):
        return {"source": source, "logged_in": False, "message": "未登录"}

    import time
    import_time = os.path.getmtime(state_file)
    now = time.time()
    hours_ago = (now - import_time) / 3600

    if hours_ago > 24:
        return {"source": source, "logged_in": False, "message": "登录已过期（超24小时）", "hours_ago": round(hours_ago, 1)}
    return {"source": source, "logged_in": True, "message": "已登录", "hours_ago": round(hours_ago, 1)}


@router.get("/login/status")
async def all_login_status():
    """Check all login statuses"""
    results = {}
    for source in LOGIN_URLS:
        status = await login_status(source)
        results[source] = status
    return {"sources": results}
