import json
import os
from typing import Any, Dict

STORE_PATH = "store.json"

DEFAULT_STORE: Dict[str, Any] = {
	"owner_id": None,
	"admins": [],
	"whitelist": [],
	"blacklist": [],
	"forced_subscription": {
		"enabled": False,
		"channel_username": None
	},
	"providers": {
		"crypto": "coingecko",  # coingecko | binance
		"fiat": "exchangerate_host"  # exchangerate_host | frankfurter
	},
	"users": [],
	"user_data": {
		# user_id -> data
	},
	"points": {
		# user_id -> score
	}
}


def get_user_data(store: Dict[str, Any], user_id: int) -> Dict[str, Any]:
	ud = store.setdefault("user_data", {})
	user = ud.setdefault(str(user_id), {
		"settings": {
			"base_fiat": "USD",
			"ui_mode": "compact",  # compact | rich
			"language": "FA",
			"display_toman": True,
			"show_irr": True,  # نمایش ریال ایران
		},
		"watchlist": [],  # list of symbols
		"portfolio": [],  # list of {symbol, qty, avg_price}
		"alerts": [],     # list of {symbol, type, value}
	})
	return user


def load_store() -> Dict[str, Any]:
	if not os.path.exists(STORE_PATH):
		return DEFAULT_STORE.copy()
	try:
		with open(STORE_PATH, "r", encoding="utf-8") as f:
			data = json.load(f)
			# ensure keys
			merged = DEFAULT_STORE.copy()
			merged.update(data)
			return merged
	except Exception:
		return DEFAULT_STORE.copy()


def save_store(data: Dict[str, Any]) -> None:
	with open(STORE_PATH, "w", encoding="utf-8") as f:
		json.dump(data, f, ensure_ascii=False, indent=2)


def is_admin(user_id: int, store: Dict[str, Any]) -> bool:
	return user_id == store.get("owner_id") or user_id in set(store.get("admins", []))
