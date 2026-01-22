import time
import json
import random
from datetime import datetime
from threading import Lock
import pyperclip
from playwright.sync_api import sync_playwright

# ================= FILES =================
STATS_FILE = "stats.json"
CONTROL_FILE = "control.json"

with open("gc_links.txt", "r", encoding="utf-8") as f:
    GC_LINKS = [x.strip() for x in f if x.strip()]

with open("message.txt", "r", encoding="utf-8") as f:
    MESSAGE = f.read().strip()

with open("group_name.txt", "r", encoding="utf-8") as f:
    content = f.read().strip()
    GROUP_NAMES = [x.strip() for x in content.split(",") if x.strip()]

ACCOUNTS = []
with open("credentials.txt", "r", encoding="utf-8") as f:
    for line in f:
        if "=" in line:
            acc, sess = line.strip().split("=", 1)
            ACCOUNTS.append((acc, sess))

stats_lock = Lock()

# ================= STATS HELPERS =================
def load_stats():
    with stats_lock:
        with open(STATS_FILE, "r") as f:
            return json.load(f)

def save_stats(stats):
    with stats_lock:
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f, indent=2)

def log_event(msg):
    stats = load_stats()
    stats["last_action"] = msg
    stats["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    stats["logs"] = stats["logs"][-200:]
    save_stats(stats)

def should_run():
    with open(CONTROL_FILE, "r") as f:
        return json.load(f).get("run", False)

def human_delay(a=1.2, b=3.0):
    time.sleep(random.uniform(a, b))

# ================= MAIN BOT =================
def main():
    cycle = 0

    with sync_playwright() as p:
        while True:
            if not should_run():
                log_event("⏸ Bot paused from dashboard")
                time.sleep(5)
                continue

            acc_name, SESSION_ID = ACCOUNTS[cycle % len(ACCOUNTS)]
            current_name = GROUP_NAMES[cycle % len(GROUP_NAMES)]

            stats = load_stats()
            stats["status"] = "running"
            stats["current_account"] = acc_name
            save_stats(stats)

            log_event(f"▶ Cycle {cycle+1} started with {acc_name}")

            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                viewport={"width": 1366, "height": 768}
            )

            page = context.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            )

            # Login via cookie
            page.goto("https://www.instagram.com/", timeout=60000)
            context.add_cookies([{
                "name": "sessionid",
                "value": SESSION_ID,
                "domain": ".instagram.com",
                "path": "/"
            }])
            page.reload()
            time.sleep(3)

            page.goto("https://www.instagram.com/direct/inbox/", timeout=60000)
            time.sleep(2)

            for link in GC_LINKS:
                if not should_run():
                    break

                try:
                    page.goto(link, timeout=60000)
                    time.sleep(2)

                    box = page.locator("div[contenteditable='true'][role='textbox']")
                    box.wait_for(timeout=5000)
                    pyperclip.copy(MESSAGE)
                    box.click()
                    box.press("Control+V")
                    box.press("Enter")

                    stats = load_stats()
                    stats["messages_sent"] += 1
                    stats["groups_processed"] += 1
                    stats["accounts"].setdefault(acc_name, {"messages": 0, "failures": 0})
                    stats["accounts"][acc_name]["messages"] += 1
                    save_stats(stats)

                    log_event("📩 Message sent")
                    human_delay()

                except Exception as e:
                    stats = load_stats()
                    stats["failures"] += 1
                    stats["accounts"].setdefault(acc_name, {"messages": 0, "failures": 0})
                    stats["accounts"][acc_name]["failures"] += 1
                    save_stats(stats)
                    log_event(f"❌ Error: {e}")

            browser.close()

            stats = load_stats()
            stats["cycles"] += 1
            stats["status"] = "idle"
            save_stats(stats)

            log_event(f"✅ Cycle {cycle+1} completed")
            cycle += 1
            time.sleep(60)

if __name__ == "__main__":
    main()

