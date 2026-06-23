import asyncio
import base64
import json
import logging
import os
import time
from datetime import datetime
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

STATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "browser_states"
)

SITES = {
    "boss": {
        "name": "BOSS直聘",
        "login_url": "https://www.zhipin.com/web/user/?ka=header-login",
        "success_indicators": ["zhipin.com/web/geek", "zhipin.com/web/chat"],
    },
    "liepin": {
        "name": "猎聘",
        "login_url": "https://www.liepin.com/login/",
        "success_indicators": ["liepin.com/zhaopin", "liepin.com/account"],
    },
    "zhaopin": {
        "name": "智联招聘",
        "login_url": "https://passport.zhaopin.com/login",
        "success_indicators": ["zhaopin.com/company", "sou.zhaopin.com"],
    },
    "guopin": {
        "name": "国聘",
        "login_url": "https://www.iguopin.com/login",
        "success_indicators": ["iguopin.com/home", "iguopin.com/search"],
    },
}

LOGIN_TIMEOUT = 300
_active_sessions: dict[str, dict] = {}


async def _detect_login(source: str, page, context, browser, playwright_obj):
    """Background task: poll for login success, save state when detected."""
    site = SITES[source]
    start = time.time()
    try:
        while time.time() - start < LOGIN_TIMEOUT:
            await asyncio.sleep(2)
            try:
                url = page.url
                for indicator in site["success_indicators"]:
                    if indicator in url:
                        await _save_and_cleanup(source, page, context, browser, playwright_obj, True)
                        return
                if "login" not in url.lower() and "passport" not in url.lower():
                    body_text = await page.inner_text("body")
                    if len(body_text.strip()) > 200:
                        await _save_and_cleanup(source, page, context, browser, playwright_obj, True)
                        return
            except Exception:
                continue
        # Timeout
        await _save_and_cleanup(source, page, context, browser, playwright_obj, False)
    except Exception as e:
        logger.warning(f"Login detection error for {source}: {e}")
        _active_sessions.pop(source, None)


async def _save_and_cleanup(source, page, context, browser, playwright_obj, success: bool):
    os.makedirs(STATE_DIR, exist_ok=True)
    state_file = os.path.join(STATE_DIR, f"{source}_state.json")
    meta_file = os.path.join(STATE_DIR, f"{source}_meta.json")

    current_url = page.url
    await context.storage_state(path=state_file)

    meta = {
        "source": source,
        "site": SITES[source]["name"],
        "saved_at": datetime.now().isoformat(),
        "url_at_save": current_url,
        "login_detected": success,
    }
    with open(meta_file, "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    logger.info(f"[LoginProxy] {source}: login={'OK' if success else 'timeout'}, state saved")
    await context.close()
    await browser.close()
    await playwright_obj.__aexit__(None, None, None)
    session = _active_sessions.get(source)
    if session:
        session["logged_in"] = success
        session["page"] = None


async def start_login(source: str) -> dict:
    if source not in SITES:
        raise ValueError(f"不支持的来源: {source}")

    # Clean up existing session
    existing = _active_sessions.pop(source, None)
    if existing:
        try:
            await existing["page"].context.browser.close()
        except Exception:
            pass

    p = await async_playwright().__aenter__()
    browser = await p.firefox.launch(headless=True)
    context = await browser.new_context(viewport={"width": 1280, "height": 800}, locale="zh-CN")
    page = await context.new_page()

    await page.goto(SITES[source]["login_url"], timeout=30000, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    screenshot = await page.screenshot(type="png")
    img_b64 = base64.b64encode(screenshot).decode()

    task = asyncio.create_task(_detect_login(source, page, context, browser, p))

    _active_sessions[source] = {
        "browser": browser,
        "context": context,
        "page": page,
        "playwright": p,
        "task": task,
        "logged_in": False,
        "started_at": time.time(),
    }

    return {"screenshot": img_b64, "status": "pending"}


async def get_login_status(source: str) -> dict:
    session = _active_sessions.get(source)
    if not session:
        return {"logged_in": False, "active": False, "message": "没有活跃的登录会话"}

    if session["logged_in"]:
        _active_sessions.pop(source, None)
        return {"logged_in": True, "active": False, "message": "登录成功"}

    elapsed = time.time() - session["started_at"]
    if elapsed > LOGIN_TIMEOUT:
        _active_sessions.pop(source, None)
        return {"logged_in": False, "active": False, "message": "登录超时，请重试"}

    page = session.get("page")
    screenshot = None
    if page:
        try:
            img = await page.screenshot(type="png")
            screenshot = base64.b64encode(img).decode()
        except Exception:
            pass

    return {"logged_in": False, "active": True, "screenshot": screenshot, "message": "等待扫码..."}


async def refresh_screenshot(source: str) -> dict:
    session = _active_sessions.get(source)
    if not session or not session.get("page"):
        raise ValueError("没有活跃的登录会话")

    await session["page"].reload(wait_until="domcontentloaded")
    await session["page"].wait_for_timeout(2000)

    img = await session["page"].screenshot(type="png")
    return {"screenshot": base64.b64encode(img).decode()}


async def cancel_login(source: str):
    session = _active_sessions.pop(source, None)
    if session:
        try:
            session["task"].cancel()
        except Exception:
            pass
        try:
            await session["browser"].close()
        except Exception:
            pass
