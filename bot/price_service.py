import asyncio
from typing import Dict, Optional, Tuple
import aiohttp
import hmac
import hashlib
import time
from store import load_store
# Import config values safely
try:
    from config import TABDEAL_API_URL, TABDEAL_API_KEY, TABDEAL_API_SECRET, BRS_API_URL, BRS_API_KEY
except ImportError:
    # Fallback values if config is not available
    TABDEAL_API_URL = "https://api1.tabdeal.org/r/api/v1"
    TABDEAL_API_KEY = "einA3WTAOWYvNeBR9cdHIB6Tqbw3dkajeWJ8FSRqp3JHy5gr2STfoYMYWBXNa86X"
    TABDEAL_API_SECRET = "TCzV5MY85pJe5O8NmhnsO6kGKo1X1jwIZm2XJifJtDbVaylEotj5TaNSykXnGWZP"
    BRS_API_URL = "https://brsapi.ir/Api/Panel"
    BRS_API_KEY = "BcFwJ8XAXX2SixD6f5UXuIx3cA5b7CBq"

COINGECKO_API = "https://api.coingecko.com/api/v3"
BINANCE_API = "https://api.binance.com/api/v3"

# Complete symbol->id mapping for all supported cryptocurrencies
SYMBOL_TO_CG_ID: Dict[str, str] = {
	# ارزهای اصلی درخواستی
	"usdt": "tether",
	"trx": "tron",
	"ton": "the-open-network",
	"btc": "bitcoin",
	"etc": "ethereum-classic",
	
	# ارزهای محبوب اصلی
	"eth": "ethereum",
	"bnb": "binancecoin",
	"sol": "solana",
	"xrp": "ripple",
	"ada": "cardano",
	"doge": "dogecoin",
	"ltc": "litecoin",
	"dot": "polkadot",
	"matic": "matic-network",
	"link": "chainlink",
	"avax": "avalanche-2",
	"uni": "uniswap",
	"atom": "cosmos",
	"xlm": "stellar",
	"bch": "bitcoin-cash",
	"fil": "filecoin",
	"near": "near",
	"algo": "algorand",
	"vet": "vechain",
	"icp": "internet-computer",
	"ftm": "fantom",
	"mana": "decentraland",
	"sand": "the-sandbox",
	"axs": "axie-infinity",
	"gala": "gala",
	"chz": "chiliz",
	"enj": "enjincoin",
	"theta": "theta-token",
	"eos": "eos",
	"aave": "aave",
	"comp": "compound-governance-token",
	"mkr": "maker",
	"snx": "havven",
	"crv": "curve-dao-token",
	"yfi": "yearn-finance",
	"sushi": "sushiswap",
	"1inch": "1inch",
	"zec": "zcash",
	"xmr": "monero",
	"dash": "dash",
	"neo": "neo",
	"qtum": "qtum",
	"iota": "iota",
	"xtz": "tezos",
	"hbar": "hedera-hashgraph",
	"grt": "the-graph",
	"bat": "basic-attention-token",
	"hot": "holo",
	"zil": "zilliqa",
	"waves": "waves",
	"rvn": "ravencoin",
	"nano": "nano",
	"btt": "bittorrent",
	"win": "wink",
	"cake": "pancakeswap-token",
	"bake": "bakerytoken",
	"auto": "auto",
	"alpha": "alpha-finance",
	"bel": "bella-protocol",
	"ctsi": "cartesi",
	"dego": "dego-finance",
	"dodo": "dodo",
	"dusk": "dusk-network",
	"egld": "elrond-erd-2",
	"flow": "flow",
	"hive": "hive",
	"icx": "icon",
	"kava": "kava",
	"ksm": "kusama",
	"lrc": "loopring",
	"omg": "omg",
	"ont": "ontology",
	"paxg": "pax-gold",
	"ren": "republic-protocol",
	"rsr": "reserve-rights-token",
	"skl": "skale",
	"storj": "storj",
	"sxp": "swipe",
	"tfuel": "theta-fuel",
	"tomo": "tomochain",
	"wrx": "wazirx",
	"zrx": "0x",
	"ankr": "ankr",
	"ar": "arweave",
	"bico": "biconomy",
	"blz": "bluzelle",
	"bond": "barnbridge",
	"c98": "coin98",
	"celo": "celo",
	"chr": "chromaway",
	"ckb": "nervos-network",
	"clv": "clover-finance",
	"cocos": "cocos-bcx",
	"cos": "contentos",
	"ctxc": "cortex",
	"cvp": "powerpool",
	"data": "streamr",
	"dgb": "digibyte",
	"dydx": "dydx",
	"elf": "aelf",
	"ern": "ethernity",
	"fetch": "fetch-ai",
	"forth": "ampleforth-governance-token",
	"front": "frontier",
	"ftt": "ftx-token",
	"fxs": "frax-share",
	"gtc": "gitcoin",
	"hard": "hard-protocol",
	"hbtc": "huobi-btc",
	"hnt": "helium",
	"idex": "idex",
	"ilv": "illuvium",
	"imx": "immutable-x",
	"inj": "injective-protocol",
	"iotx": "iotex",
	"jasmy": "jasmycoin",
	"keep": "keep-network",
	"klay": "klaytn",
	"knc": "kyber-network-crystal",
	"ldo": "lido-dao",
	"lina": "linear",
	"lit": "litentry",
	"lpt": "livepeer",
	"lqty": "liquity",
	"lto": "lto-network",
	"luna": "terra-luna",
	"mask": "mask-network",
	"mbox": "mobox",
	"mc": "merit-circle",
	"mina": "mina-protocol",
	"mir": "mirror-protocol",
	"mln": "melon",
	"movr": "moonriver",
	"mtl": "metal",
	"multi": "multichain",
	"nmr": "numeraire",
	"ocean": "ocean-protocol",
	"ogn": "origin-protocol",
	"om": "mantra-dao",
	"one": "harmony",
	"ong": "ong",
	"op": "optimism",
	"orbs": "orbs",
	"orn": "orion-protocol",
	"oxt": "orchid-protocol",
	"pax": "paxos-standard",
	"people": "constitution-dao",
	"perp": "perpetual-protocol",
	"pols": "polkastarter",
	"poly": "polymath",
	"pond": "marlin",
	"powr": "power-ledger",
	"pro": "propy",
	"pundix": "pundi-x",
	"pyr": "vulcan-forged",
	"qi": "benqi",
	"qnt": "quant-network",
	"quick": "quickswap",
	"rad": "radicle",
	"rare": "superrare",
	"ray": "raydium",
	"reef": "reef",
	"req": "request-network",
	"rlc": "iexec-rlc",
	"rose": "oasis-network",
	"rune": "thorchain",
	"scrt": "secret",
	"shib": "shiba-inu",
	"slp": "smooth-love-potion",
	"snt": "status",
	"spell": "spell-token",
	"srm": "serum",
	"stpt": "stpt",
	"strax": "stratis",
	"super": "superfarm",
	"swrv": "swerve",
	"syn": "synapse-2",
	"tlm": "alien-worlds",
	"trb": "tellor",
	"tribe": "tribe",
	"tru": "truefi",
	"tvk": "the-virtua-kolect",
	"uma": "uma",
	"unfi": "unifi-protocol-dao",
	"usdc": "usd-coin",
	"utk": "utrust",
	"vgx": "voyager-token",
	"vtho": "vethor-token",
	"waxp": "wax",
	"wbtc": "wrapped-bitcoin",
	"weth": "wrapped-ethereum",
	"woo": "woo-network",
	"xec": "ecash",
	"xem": "nem",
	"xvg": "verge",
	"ygg": "yield-guild-games",
	"zen": "horizen",
}


async def fetch_json(session: aiohttp.ClientSession, url: str, params: Optional[Dict[str, str]] = None) -> dict:
	async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
		resp.raise_for_status()
		return await resp.json()


async def get_price_by_cgid(coin_id: str) -> Optional[Tuple[float, Optional[float]]]:
	"""Return (usd_price, usd_24h_change) or None if not found."""
	url = f"{COINGECKO_API}/simple/price"
	params = {
		"ids": coin_id,
		"vs_currencies": "usd",
		"include_24hr_change": "true",
	}
	async with aiohttp.ClientSession() as session:
		try:
			data = await fetch_json(session, url, params)
			info = data.get(coin_id)
			if not info:
				return None
			price = float(info.get("usd"))
			change = info.get("usd_24h_change")
			return price, (float(change) if change is not None else None)
		except Exception:
			return None


async def get_price_by_symbol(symbol: str) -> Optional[Tuple[str, float, Optional[float]]]:
	"""Lookup by common ticker symbol; returns (symbol, price, change)."""
	sym = symbol.strip().lower()
	coin_id = SYMBOL_TO_CG_ID.get(sym)
	if not coin_id:
		return None
	result = await get_price_by_cgid(coin_id)
	if result is None:
		return None
	price, change = result
	return sym.upper(), price, change


async def get_price_by_symbol_binance(symbol: str) -> Optional[Tuple[str, float, Optional[float]]]:
	"""Binance spot price for symbolUSDT, change via 24hr ticker."""
	sym = symbol.strip().upper()
	pair = f"{sym}USDT"
	try:
		async with aiohttp.ClientSession() as session:
			# price
			async with session.get(f"{BINANCE_API}/ticker/price", params={"symbol": pair}, timeout=aiohttp.ClientTimeout(total=10)) as r:
				r.raise_for_status()
				p = await r.json()
				price = float(p.get("price"))
			# change
			async with session.get(f"{BINANCE_API}/ticker/24hr", params={"symbol": pair}, timeout=aiohttp.ClientTimeout(total=10)) as r2:
				r2.raise_for_status()
				j = await r2.json()
				change = float(j.get("priceChangePercent")) if j.get("priceChangePercent") is not None else None
			return sym, price, change
	except Exception:
		return None


async def get_crypto_price_with_provider(symbol: str, provider: str) -> Optional[Tuple[str, float, Optional[float]]]:
	"""Get crypto price with specified provider. Returns (symbol, price, 24h_change) or None."""
	symbol = symbol.lower()
	
	# بررسی اینکه آیا ارز در لیست فعال است یا نه
	store = load_store()
	enabled_currencies = store.get('enabled_currencies', {})
	
	if symbol not in enabled_currencies:
		# اگر ارز در لیست فعال نیست، از API های پیش‌فرض استفاده کن
		provider_key = (provider or "").lower()
		if provider_key == "binance":
			res = await get_price_by_symbol_binance(symbol)
			if res:
				return res
		return await get_price_by_symbol(symbol)
	
	currency_data = enabled_currencies[symbol]
	if not currency_data.get('enabled', False):
		return None
	
	# استفاده از API ثبت شده
	api_id = currency_data.get('api')
	if api_id:
		api_configs = store.get('api_configs', {})
		api_config = api_configs.get(api_id)
		
		if api_config and api_config.get('enabled', False):
			# استفاده از API سفارشی
			result = await get_price_from_custom_api(symbol, api_config)
			if result:
				return result
	
	# استفاده از API های پیش‌فرض
	provider_key = (provider or "").lower()
	
	# اولویت: Tabdeal > Binance > CoinGecko
	if provider_key == "tabdeal":
		res = await get_tabdeal_price(symbol)
		if res:
			price, change_24h = res
			return symbol.upper(), price, change_24h
	elif provider_key == "binance":
		res = await get_price_by_symbol_binance(symbol)
		if res:
			return res
	
	# Fallback به Tabdeal اگر provider مشخص نشده
	if not provider_key or provider_key == "coingecko":
		res = await get_tabdeal_price(symbol)
		if res:
			price, change_24h = res
			return symbol.upper(), price, change_24h
	
	# آخرین fallback به CoinGecko
	return await get_price_by_symbol(symbol)

async def get_price_from_custom_api(symbol: str, api_config: dict) -> Optional[Tuple[str, float, Optional[float]]]:
	"""دریافت قیمت از API سفارشی"""
	try:
		api_type = api_config.get('type', 'crypto')
		api_key = api_config.get('key', '')
		api_url = api_config.get('url', '')
		
		if api_type == 'crypto':
			if 'coingecko' in api_url.lower():
				return await get_price_from_coingecko_api(symbol, api_key, api_url)
			elif 'binance' in api_url.lower():
				return await get_price_from_binance_api(symbol, api_key, api_url)
			else:
				# API سفارشی دیگر
				return await get_price_from_generic_api(symbol, api_config)
		
		return None
		
	except Exception as e:
		print(f"خطا در دریافت قیمت از API سفارشی: {e}")
		return None

async def get_price_from_coingecko_api(symbol: str, api_key: str, api_url: str) -> Optional[Tuple[str, float, Optional[float]]]:
	"""دریافت قیمت از CoinGecko API سفارشی"""
	try:
		coin_id = SYMBOL_TO_CG_ID.get(symbol.lower())
		if not coin_id:
			return None
		
		url = f"{api_url}/simple/price"
		params = {
			"ids": coin_id,
			"vs_currencies": "usd",
			"include_24hr_change": "true",
		}
		
		if api_key:
			params["x_cg_demo_api_key"] = api_key
		
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
				if resp.status == 200:
					data = await resp.json()
					info = data.get(coin_id)
					if info:
						price = float(info.get("usd", 0))
						change = info.get("usd_24h_change")
						change = float(change) if change is not None else None
						return symbol.upper(), price, change
		
		return None
		
	except Exception as e:
		print(f"خطا در دریافت قیمت از CoinGecko API: {e}")
		return None

async def get_price_from_binance_api(symbol: str, api_key: str, api_url: str) -> Optional[Tuple[str, float, Optional[float]]]:
	"""دریافت قیمت از Binance API سفارشی"""
	try:
		symbol = symbol.upper() + "USDT"
		url = f"{api_url}/ticker/24hr"
		params = {"symbol": symbol}
		
		headers = {}
		if api_key:
			headers["X-MBX-APIKEY"] = api_key
		
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
				if resp.status == 200:
					data = await resp.json()
					price = float(data.get("lastPrice", 0))
					change = float(data.get("priceChangePercent", 0))
					return symbol.replace("USDT", ""), price, change
		
		return None
		
	except Exception as e:
		print(f"خطا در دریافت قیمت از Binance API: {e}")
		return None

async def get_price_from_generic_api(symbol: str, api_config: dict) -> Optional[Tuple[str, float, Optional[float]]]:
	"""دریافت قیمت از API عمومی"""
	try:
		api_url = api_config.get('url', '')
		api_key = api_config.get('key', '')
		
		# ساخت URL با پارامترها
		url = f"{api_url}/price/{symbol.upper()}"
		
		headers = {}
		if api_key:
			headers["Authorization"] = f"Bearer {api_key}"
			headers["X-API-Key"] = api_key
		
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
				if resp.status == 200:
					data = await resp.json()
					
					# تلاش برای استخراج قیمت از پاسخ
					price = None
					change = None
					
					if isinstance(data, dict):
						price = data.get("price") or data.get("last") or data.get("close")
						change = data.get("change_24h") or data.get("change_percent") or data.get("change")
					
					if price:
						price = float(price)
						change = float(change) if change is not None else None
						return symbol.upper(), price, change
		
		return None
		
	except Exception as e:
		print(f"خطا در دریافت قیمت از API عمومی: {e}")
		return None

def format_price_message(symbol: str, price: float, change_24h: Optional[float]) -> str:
	arrow = "" if change_24h is None else ("📈" if change_24h >= 0 else "📉")
	change_txt = "نامشخص" if change_24h is None else f"{change_24h:.2f}% {arrow}"
	return (
		f"قیمت لحظه‌ای {symbol}:\n"
		f"💵 {price:,.4f} دلار\n"
		f"تغییر ۲۴ساعته: {change_txt}"
	)


async def get_tabdeal_price(symbol: str) -> Optional[Tuple[float, Optional[float]]]:
	"""دریافت قیمت از API Tabdeal"""
	try:
		# ایجاد signature برای Tabdeal API
		timestamp = str(int(time.time() * 1000))
		message = f"{TABDEAL_API_KEY}{timestamp}"
		signature = hmac.new(
			TABDEAL_API_SECRET.encode('utf-8'),
			message.encode('utf-8'),
			hashlib.sha256
		).hexdigest()
		
		headers = {
			'X-API-KEY': TABDEAL_API_KEY,
			'X-TIMESTAMP': timestamp,
			'X-SIGNATURE': signature,
			'Content-Type': 'application/json'
		}
		
		url = f"{TABDEAL_API_URL}/market/price"
		params = {'symbol': symbol.upper()}
		
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
				if resp.status == 200:
					data = await resp.json()
					if data.get('success') and 'data' in data:
						price_data = data['data']
						price = float(price_data.get('price', 0))
						change_24h = price_data.get('change_24h')
						if change_24h is not None:
							change_24h = float(change_24h)
						return price, change_24h
		return None
	except Exception as e:
		print(f"خطا در دریافت قیمت از Tabdeal: {e}")
		return None


async def get_brs_price(symbol: str) -> Optional[Tuple[float, Optional[float]]]:
	"""دریافت قیمت از API BRS (طلا و ارزهای داخلی)"""
	try:
		headers = {
			'Authorization': f'Bearer {BRS_API_KEY}',
			'Content-Type': 'application/json'
		}
		
		# BRS API برای طلا و ارزهای داخلی
		url = f"{BRS_API_URL}/prices"
		params = {'symbol': symbol.upper()}
		
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
				if resp.status == 200:
					data = await resp.json()
					if data.get('success') and 'data' in data:
						price_data = data['data']
						price = float(price_data.get('price', 0))
						change_24h = price_data.get('change_24h')
						if change_24h is not None:
							change_24h = float(change_24h)
						return price, change_24h
		return None
	except Exception as e:
		print(f"خطا در دریافت قیمت از BRS: {e}")
		return None


if __name__ == "__main__":
	# Quick manual test
	async def _test():
		for sym in ["btc", "eth", "sol", "xrp"]:
			print("Testing", sym)
			res = await get_price_by_symbol(sym)
			print(res)
	asyncio.run(_test())
