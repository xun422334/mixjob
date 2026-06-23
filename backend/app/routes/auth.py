import os
import shutil
import subprocess
from fastapi import APIRouter, HTTPException, UploadFile, File
from ..services.login_proxy import (
    start_login, get_login_status, refresh_screenshot, cancel_login, SITES as PROXY_SITES
)

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


def _find_python() -> str:
    """Find available python command (python3 or python)."""
    for cmd in ["python3", "python"]:
        if shutil.which(cmd):
            return cmd
    return "python3"


@router.post("/login/{source}")
async def login_source(source: str):
    """Launch Playwright browser for user to log in (local dev only)."""
    if source not in LOGIN_URLS:
        raise HTTPException(status_code=400, detail=f"不支持的来源: {source}")

    os.makedirs(BROWSER_STATE_DIR, exist_ok=True)

    script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "login_helper.py"
    )

    if not os.path.exists(script):
        raise HTTPException(status_code=500, detail="login_helper.py 不存在")

    python_cmd = _find_python()
    try:
        subprocess.Popen(
            [python_cmd, script, source],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="服务器环境不支持自动打开浏览器。请使用本地脚本登录后上传状态文件，或使用下方的'上传登录状态'功能。"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动登录浏览器失败: {str(e)}")

    return {
        "status": "browser_opened",
        "message": f"已打开{SITE_NAMES.get(source, source)}登录页面，请在浏览器中完成登录",
        "login_url": LOGIN_URLS[source],
    }


@router.post("/login/upload/{source}")
async def upload_login_state(source: str, file: UploadFile = File(...)):
    """Upload a browser state file from local login."""
    if source not in LOGIN_URLS:
        raise HTTPException(status_code=400, detail=f"不支持的来源: {source}")

    os.makedirs(BROWSER_STATE_DIR, exist_ok=True)

    state_file = os.path.join(BROWSER_STATE_DIR, f"{source}_state.json")
    with open(state_file, "wb") as f:
        content = await file.read()
        f.write(content)

    import json, time
    meta_file = os.path.join(BROWSER_STATE_DIR, f"{source}_meta.json")
    with open(meta_file, "w") as f:
        json.dump({
            "source": source,
            "site": SITE_NAMES.get(source, source),
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "uploaded": True,
        }, f, ensure_ascii=False)

    return {
        "status": "ok",
        "message": f"{SITE_NAMES.get(source, source)} 登录状态已上传",
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


# === Proxy login (server-side Playwright + screenshot for QR scan) ===

@router.post("/login/proxy/{source}")
async def proxy_login_start(source: str):
    """Start server-side Playwright browser, return QR code screenshot for scanning."""
    try:
        result = await start_login(source)
        return {
            "status": "ok",
            "source": source,
            "screenshot": f"data:image/png;base64,{result['screenshot']}",
            "session_status": result["status"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动登录失败: {str(e)}")


@router.get("/login/proxy/{source}/status")
async def proxy_login_check(source: str):
    """Check proxy login status, return fresh screenshot if still waiting."""
    try:
        result = await get_login_status(source)
        if result.get("screenshot"):
            result["screenshot"] = f"data:image/png;base64,{result['screenshot']}"
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login/proxy/{source}/refresh")
async def proxy_login_refresh(source: str):
    """Refresh the QR code on the login page."""
    try:
        result = await refresh_screenshot(source)
        return {"status": "ok", "screenshot": f"data:image/png;base64,{result['screenshot']}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login/proxy/{source}/cancel")
async def proxy_login_cancel(source: str):
    """Cancel an active proxy login session."""
    await cancel_login(source)
    return {"status": "ok", "message": "登录会话已取消"}
