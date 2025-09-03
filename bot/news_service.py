from typing import List, Optional
import asyncio
import feedparser

DEFAULT_FEEDS = [
	"https://rss.app/feeds/HD4lKI4vyn0d7F5R.xml",  # Example crypto aggregated feed
	"https://www.coindesk.com/arc/outboundfeeds/rss/",  # Coindesk
	"https://cointelegraph.com/rss",  # Cointelegraph
]


async def fetch_feed(url: str, limit: int = 5) -> List[dict]:
	loop = asyncio.get_event_loop()
	return await loop.run_in_executor(None, _parse_feed, url, limit)


def _parse_feed(url: str, limit: int) -> List[dict]:
	parsed = feedparser.parse(url)
	items = []
	for entry in parsed.entries[:limit]:
		items.append({
			"title": entry.get("title", ""),
			"link": entry.get("link", ""),
			"summary": entry.get("summary", ""),
		})
	return items


async def get_news(symbol: Optional[str] = None, per_feed: int = 3) -> List[dict]:
	results: List[dict] = []
	for url in DEFAULT_FEEDS:
		try:
			items = await fetch_feed(url, limit=per_feed)
			results.extend(items)
		except Exception:
			continue
	if symbol:
		s = symbol.strip().upper()
		results = [i for i in results if s in (i.get("title", "").upper() + i.get("summary", "").upper())]
	return results[:15]


