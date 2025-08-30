import time
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

