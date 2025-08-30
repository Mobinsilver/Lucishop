import time
import random
from typing import Dict, Tuple

from store import get_user_data, save_store, load_store

RATE_LIMIT_WINDOW = 10  # seconds
RATE_LIMIT_MAX = 12     # max messages per window


def check_black_white(user_id: int) -> Tuple[bool, str]:
	store = load_store()
	if user_id in set(store.get("blacklist", [])):
		return False, "blacklisted"
	wl = store.get("whitelist", [])
	if wl and (user_id not in set(wl)):
		return False, "not_whitelisted"
	return True, "ok"


def touch_rate_limit(user_id: int) -> Tuple[bool, str]:
	store = load_store()
	ud = get_user_data(store, user_id)
	bucket = ud.setdefault("rate", {"ts": 0, "cnt": 0})
	now = int(time.time())
	if now - bucket.get("ts", 0) > RATE_LIMIT_WINDOW:
		bucket["ts"], bucket["cnt"] = now, 1
		save_store(store)
		return True, "ok"
	else:
		bucket["cnt"] = int(bucket.get("cnt", 0)) + 1
		save_store(store)
		if bucket["cnt"] > RATE_LIMIT_MAX:
			return False, "rate_limited"
		return True, "ok"

def start_captcha(user_id: int) -> str:
	store = load_store()
	ud = get_user_data(store, user_id)
	if ud.get("captcha", {}).get("passed"):
		return "passed"
	a, b = random.randint(1, 9), random.randint(1, 9)
	ud["captcha"] = {"question": f"{a}+{b}", "answer": str(a + b), "passed": False, "ts": int(time.time())}
	save_store(store)
	return ud["captcha"]["question"]


def verify_captcha(user_id: int, answer: str) -> bool:
	store = load_store()
	ud = get_user_data(store, user_id)
	cap = ud.get("captcha") or {}
	if not cap:
		return False
	if str(cap.get("answer")) == str(answer).strip():
		ud["captcha"]["passed"] = True
		save_store(store)
		return True
	return False


