import time
from typing import Any, Dict, Optional, Tuple


class TTLCache:
	def __init__(self):
		self._store: Dict[str, Tuple[float, Any]] = {}

	def get(self, key: str) -> Optional[Any]:
		item = self._store.get(key)
		if not item:
			return None
		expire_ts, value = item
		if expire_ts < time.time():
			self._store.pop(key, None)
			return None
		return value

	def set(self, key: str, value: Any, ttl_seconds: int) -> None:
		expire_ts = time.time() + max(1, int(ttl_seconds))
		self._store[key] = (expire_ts, value)

	def clear(self) -> None:
		self._store.clear()
	
	def delete(self, key: str) -> None:
		self._store.pop(key, None)

