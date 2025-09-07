import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from cache import TTLCache

@dataclass
class Rate:
    """مدل داده برای نرخ ارز"""
    symbol: str  # برای کریپتو: BTC, ETH, etc. برای فیات: USD/IRR, EUR/IRR
    price: float
    change_pct: Optional[float] = None
    timestamp: Optional[int] = None

@dataclass
class APIHealthCheck:
    """نتیجه بررسی سلامت API"""
    ok: bool
    error: Optional[str] = None
    response_time: Optional[float] = None

class ExternalRatesClient:
    """کلاینت برای API های خارجی نرخ ارز"""
    
    def __init__(self, base_url: str, api_key: str, api_type: str, 
                 headers: Optional[Dict] = None, params: Optional[Dict] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.api_type = api_type  # 'crypto' or 'fiat'
        self.headers = headers or {}
        self.params = params or {}
        
        # تنظیم header پیش‌فرض برای API key
        if 'Authorization' not in self.headers and 'X-API-Key' not in self.headers:
            self.headers['X-API-Key'] = api_key
        
        # کش برای جلوگیری از درخواست‌های مکرر
        self.cache = TTLCache()
        
    async def healthcheck(self) -> APIHealthCheck:
        """بررسی سلامت API"""
        try:
            start_time = datetime.now()
            
            # استفاده از endpoint ساده برای تست
            test_url = f"{self.base_url}/health"
            if self.api_type == 'crypto':
                test_url = f"{self.base_url}/ping"
            elif self.api_type == 'fiat':
                test_url = f"{self.base_url}/status"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    test_url,
                    headers=self.headers,
                    params=self.params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time = (datetime.now() - start_time).total_seconds()
                    
                    if response.status == 200:
                        return APIHealthCheck(ok=True, response_time=response_time)
                    else:
                        return APIHealthCheck(
                            ok=False, 
                            error=f"HTTP {response.status}",
                            response_time=response_time
                        )
                        
        except asyncio.TimeoutError:
            return APIHealthCheck(ok=False, error="Timeout")
        except Exception as e:
            return APIHealthCheck(ok=False, error=str(e))
    
    async def get_crypto_rates(self, symbols: List[str]) -> List[Rate]:
        """دریافت نرخ ارزهای کریپتو"""
        cache_key = f"crypto_rates:{','.join(sorted(symbols))}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # ساخت URL بر اساس نوع API
            if self.api_type == 'crypto':
                url = f"{self.base_url}/crypto/rates"
                params = {**self.params, 'symbols': ','.join(symbols)}
            else:
                # اگر API فیات است، از endpoint کریپتو استفاده کن
                url = f"{self.base_url}/rates"
                params = {**self.params, 'crypto': ','.join(symbols)}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        rates = self._parse_crypto_response(data, symbols)
                        
                        # ذخیره در کش برای 30 ثانیه
                        self.cache.set(cache_key, rates, ttl_seconds=30)
                        return rates
                    else:
                        print(f"API Error: {response.status}")
                        return []
                        
        except Exception as e:
            print(f"Error fetching crypto rates: {e}")
            return []
    
    async def get_fiat_rates(self, pairs: List[str]) -> List[Rate]:
        """دریافت نرخ ارزهای فیات"""
        cache_key = f"fiat_rates:{','.join(sorted(pairs))}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # ساخت URL بر اساس نوع API
            if self.api_type == 'fiat':
                url = f"{self.base_url}/fiat/rates"
                params = {**self.params, 'pairs': ','.join(pairs)}
            else:
                # اگر API کریپتو است، از endpoint فیات استفاده کن
                url = f"{self.base_url}/rates"
                params = {**self.params, 'fiat': ','.join(pairs)}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        rates = self._parse_fiat_response(data, pairs)
                        
                        # ذخیره در کش برای 60 ثانیه
                        self.cache.set(cache_key, rates, ttl_seconds=60)
                        return rates
                    else:
                        print(f"API Error: {response.status}")
                        return []
                        
        except Exception as e:
            print(f"Error fetching fiat rates: {e}")
            return []
    
    def _parse_crypto_response(self, data: Dict, symbols: List[str]) -> List[Rate]:
        """پارس کردن پاسخ API کریپتو"""
        rates = []
        
        try:
            # تلاش برای پارس کردن فرمت‌های مختلف
            if 'data' in data:
                items = data['data']
            elif 'rates' in data:
                items = data['rates']
            elif 'prices' in data:
                items = data['prices']
            else:
                items = data
            
            for symbol in symbols:
                symbol_upper = symbol.upper()
                
                # جستجو در داده‌ها
                rate_data = None
                for item in items:
                    if isinstance(item, dict):
                        if (item.get('symbol', '').upper() == symbol_upper or 
                            item.get('currency', '').upper() == symbol_upper or
                            item.get('coin', '').upper() == symbol_upper):
                            rate_data = item
                            break
                
                if rate_data:
                    price = float(rate_data.get('price', 0))
                    change_pct = rate_data.get('change_24h', rate_data.get('change_pct'))
                    if change_pct is not None:
                        change_pct = float(change_pct)
                    
                    timestamp = rate_data.get('timestamp', rate_data.get('ts'))
                    if timestamp is None:
                        timestamp = int(datetime.now().timestamp())
                    
                    rates.append(Rate(
                        symbol=symbol_upper,
                        price=price,
                        change_pct=change_pct,
                        timestamp=timestamp
                    ))
                    
        except Exception as e:
            print(f"Error parsing crypto response: {e}")
        
        return rates
    
    def _parse_fiat_response(self, data: Dict, pairs: List[str]) -> List[Rate]:
        """پارس کردن پاسخ API فیات"""
        rates = []
        
        try:
            # تلاش برای پارس کردن فرمت‌های مختلف
            if 'data' in data:
                items = data['data']
            elif 'rates' in data:
                items = data['rates']
            elif 'pairs' in data:
                items = data['pairs']
            else:
                items = data
            
            for pair in pairs:
                pair_upper = pair.upper()
                
                # جستجو در داده‌ها
                rate_data = None
                for item in items:
                    if isinstance(item, dict):
                        if (item.get('pair', '').upper() == pair_upper or 
                            item.get('currency_pair', '').upper() == pair_upper or
                            item.get('symbol', '').upper() == pair_upper):
                            rate_data = item
                            break
                
                if rate_data:
                    price = float(rate_data.get('rate', rate_data.get('price', 0)))
                    change_pct = rate_data.get('change_24h', rate_data.get('change_pct'))
                    if change_pct is not None:
                        change_pct = float(change_pct)
                    
                    timestamp = rate_data.get('timestamp', rate_data.get('ts'))
                    if timestamp is None:
                        timestamp = int(datetime.now().timestamp())
                    
                    rates.append(Rate(
                        symbol=pair_upper,
                        price=price,
                        change_pct=change_pct,
                        timestamp=timestamp
                    ))
                    
        except Exception as e:
            print(f"Error parsing fiat response: {e}")
        
        return rates

class ExternalAPIManager:
    """مدیریت API های خارجی"""
    
    def __init__(self, store):
        self.store = store
        self.clients = {}  # کش کلاینت‌ها
        self._load_api_configs()
    
    def _load_api_configs(self):
        """بارگذاری تنظیمات API از store"""
        self.api_configs = self.store.get('external_api_configs', {})
    
    def save_api_config(self, config: Dict) -> bool:
        """ذخیره تنظیمات API"""
        try:
            if 'external_api_configs' not in self.store:
                self.store['external_api_configs'] = {}
            
            self.store['external_api_configs'] = config
            self.api_configs = config
            
            # پاک کردن کش کلاینت‌ها
            self.clients.clear()
            
            return True
        except Exception as e:
            print(f"Error saving API config: {e}")
            return False
    
    def get_api_config(self) -> Optional[Dict]:
        """دریافت تنظیمات API فعلی"""
        return self.api_configs
    
    def get_client(self) -> Optional[ExternalRatesClient]:
        """دریافت کلاینت API"""
        if not self.api_configs:
            return None
        
        # بررسی کش
        cache_key = f"client_{hash(str(self.api_configs))}"
        if cache_key in self.clients:
            return self.clients[cache_key]
        
        try:
            client = ExternalRatesClient(
                base_url=self.api_configs.get('base_url', ''),
                api_key=self.api_configs.get('api_key', ''),
                api_type=self.api_configs.get('type', 'crypto'),
                headers=self.api_configs.get('headers', {}),
                params=self.api_configs.get('params', {})
            )
            
            self.clients[cache_key] = client
            return client
        except Exception as e:
            print(f"Error creating API client: {e}")
            return None
    
    async def test_connection(self) -> APIHealthCheck:
        """تست اتصال به API"""
        client = self.get_client()
        if not client:
            return APIHealthCheck(ok=False, error="API not configured")
        
        return await client.healthcheck()
    
    async def get_crypto_rates(self, symbols: List[str]) -> List[Rate]:
        """دریافت نرخ ارزهای کریپتو"""
        client = self.get_client()
        if not client:
            return []
        
        return await client.get_crypto_rates(symbols)
    
    async def get_fiat_rates(self, pairs: List[str]) -> List[Rate]:
        """دریافت نرخ ارزهای فیات"""
        client = self.get_client()
        if not client:
            return []
        
        return await client.get_fiat_rates(pairs)
