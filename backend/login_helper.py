"""
登录助手 - 打开浏览器让你手动登录招聘网站，自动检测登录完成并保存状态

用法:
  python3 login_helper.py boss    # 登录BOSS直聘
  python3 login_helper.py maimai  # 登录脉脉
  python3 login_helper.py status  # 查看已有登录状态
"""
import sys
import asyncio
import os
import json
from datetime import datetime

STATE_DIR = os.path.join(os.path.dirname(__file__), "browser_states")
os.makedirs(STATE_DIR, exist_ok=True)

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

LOGIN_TIMEOUT_SECONDS = 300  # 5 minutes max wait


async def login_site(source: str):
    if source not in SITES:
        print(f"Unsupported source: {source}")
        print(f"Available: {', '.join(SITES.keys())}")
        sys.exit(1)

    site = SITES[source]
    state_file = os.path.join(STATE_DIR, f"{source}_state.json")
    meta_file = os.path.join(STATE_DIR, f"{source}_meta.json")

    print(f"Opening browser for {site['name']} login...")
    print(f"Login URL: {site['login_url']}")
    print(f"You have {LOGIN_TIMEOUT_SECONDS // 60} minutes to complete login.")
    print("The browser will close automatically once login is detected.")

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )
        page = await context.new_page()

        await page.goto(site["login_url"], timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # Poll for login success
        start_time = datetime.now()
        logged_in = False
        while (datetime.now() - start_time).total_seconds() < LOGIN_TIMEOUT_SECONDS:
            await asyncio.sleep(2)
            try:
                current_url = page.url
                for indicator in site["success_indicators"]:
                    if indicator in current_url:
                        logged_in = True
                        break
                if logged_in:
                    break
                # Also check if login-related elements are gone
                if "login" not in current_url.lower() and "passport" not in current_url.lower():
                    # Verify page has actual content (not blank)
                    body_text = await page.inner_text("body")
                    if len(body_text.strip()) > 200:
                        logged_in = True
                        break
            except Exception:
                continue

        if logged_in:
            print(f"Login detected! Saving state...")
        else:
            print(f"Timeout reached. Saving current state anyway...")

        current_url = page.url
        await context.storage_state(path=state_file)

        meta = {
            "source": source,
            "site": site["name"],
            "saved_at": datetime.now().isoformat(),
            "url_at_save": current_url,
            "login_detected": logged_in,
        }
        with open(meta_file, "w") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        print(f"Login state saved to: {state_file}")
        if logged_in:
            print("Login successful!")
        else:
            print("Note: Login may not have completed. You can try again.")

        await browser.close()


def check_status():
    print("\nLogin status:\n")
    for source, site in SITES.items():
        state_file = os.path.join(STATE_DIR, f"{source}_state.json")
        meta_file = os.path.join(STATE_DIR, f"{source}_meta.json")
        if os.path.exists(state_file):
            stat = os.stat(state_file)
            age_hours = (datetime.now().timestamp() - stat.st_mtime) / 3600
            status = "OK" if age_hours < 24 else "possibly expired"
            extra = ""
            if os.path.exists(meta_file):
                with open(meta_file) as f:
                    meta = json.load(f)
                    extra = f" saved at {meta.get('saved_at', '?')}"
            print(f"  [{site['name']}] {status} ({age_hours:.1f}h ago{extra})")
        else:
            print(f"  [{site['name']}] not logged in")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "status":
        check_status()
    else:
        asyncio.run(login_site(sys.argv[1]))
