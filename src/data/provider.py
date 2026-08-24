"""
Универсальный провайдер данных для Московской биржи.
Загружает ВСЕ доступные данные через пагинацию MOEX ISS API.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import pandas as pd
import requests
import yaml

logger = logging.getLogger(__name__)


class DataProvider(ABC):
    """Абстрактный базовый класс для провайдеров данных."""
    
    @abstractmethod
    def get_historical_data(
        self,
        ticker: str,
        interval: str,
        days_back: int,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        pass


class MoexISSProvider(DataProvider):
    """
    Универсальный провайдер данных через MOEX ISS.
    Загружает ВСЕ доступные данные через пагинацию.
    """
    
    BASE_URL = "https://iss.moex.com/iss"
    PAGE_SIZE = 500  # MOEX ограничивает 500 свечами за запрос
    
    KNOWN_INSTRUMENTS = {
        "IMOEXF": {"engine": "futures", "market": "forts", "board": "RFUD"},
        "RIMIXF": {"engine": "futures", "market": "forts", "board": "RFUD"},
        "SBERF": {"engine": "futures", "market": "forts", "board": "RFUD"},
        "SBER": {"engine": "stock", "market": "shares", "board": "TQBR"},
        "GAZP": {"engine": "stock", "market": "shares", "board": "TQBR"},
        "LKOH": {"engine": "stock", "market": "shares", "board": "TQBR"},
        "VTBR": {"engine": "stock", "market": "shares", "board": "TQBR"},
        "YAND": {"engine": "stock", "market": "shares", "board": "TQBR"},
        "IMOEX": {"engine": "stock", "market": "index", "board": "SESQ"},
    }
    
    def __init__(self, cache_dir: str = "data"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ICT-Backtester-RU/1.0",
            "Accept": "application/json"
        })
        logger.info("MOEX ISS провайдер инициализирован")
    
    def get_historical_data(
        self,
        ticker: str,
        interval: str,
        days_back: int,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Загрузить ВСЕ данные с MOEX ISS через пагинацию."""
        
        # Проверяем кэш
        cache_file = self.cache_dir / f"{ticker}_{interval}_{days_back}d.parquet"
        if cache_file.exists():
            logger.info(f"Загрузка данных из кэша: {cache_file}")
            df = pd.read_parquet(cache_file)
            logger.info(f"Загружено из кэша: {len(df)} свечей")
            return df
        
        logger.info(f"Загрузка ВСЕХ данных {ticker} с MOEX ISS...")
        
        if end_date is None:
            end_date = datetime.now()
        
        start_date = end_date - timedelta(days=days_back)
        
        # Маппинг интервалов
        interval_map = {
            "1min": 1,
            "10min": 10,
            "1h": 60,
            "1d": 24,
        }
        
        moex_interval = interval_map.get(interval)
        if moex_interval is None:
            if interval == "5min":
                moex_interval = 10
                logger.warning("5min не поддерживается, используем 10min")
            elif interval == "15min":
                moex_interval = 60
                logger.warning("15min не поддерживается, используем 1h")
            else:
                raise ValueError(f"Неподдерживаемый интервал: {interval}")
        
        try:
            instrument_info = self._get_instrument_info(ticker)
            logger.info(f"Параметры: {instrument_info}")
            
            # Загружаем ВСЕ данные через пагинацию
            df = self._fetch_all_candles(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                interval=moex_interval,
                instrument_info=instrument_info
            )
            
            if df.empty:
                raise ValueError(f"Не удалось загрузить данные для {ticker}")
            
            # Сохраняем в кэш
            df.to_parquet(cache_file)
            logger.info(f"Все данные сохранены в кэш: {cache_file}")
            logger.info(f"ИТОГО загружено: {len(df)} свечей")
            
            return df
            
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            raise
    
    def _get_instrument_info(self, ticker: str) -> Dict[str, str]:
        """Получить информацию об инструменте."""
        if ticker in self.KNOWN_INSTRUMENTS:
            return self.KNOWN_INSTRUMENTS[ticker]
        
        logger.warning(f"Тикер {ticker} неизвестен, используем fallback")
        return self._fallback_instrument_info(ticker)
    
    def _fallback_instrument_info(self, ticker: str) -> Dict[str, str]:
        """Fallback определение."""
        if ticker.endswith("F") or (len(ticker) >= 3 and ticker[-2].isalpha() and ticker[-1].isdigit()):
            return {"engine": "futures", "market": "forts", "board": "RFUD"}
        else:
            return {"engine": "stock", "market": "shares", "board": "TQBR"}
    
    def _fetch_all_candles(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: int,
        instrument_info: Dict[str, str]
    ) -> pd.DataFrame:
        """Загрузить ВСЕ свечи через пагинацию."""
        
        engine = instrument_info["engine"]
        market = instrument_info["market"]
        board = instrument_info["board"]
        
        url = (
            f"{self.BASE_URL}/engines/{engine}/markets/{market}"
            f"/boards/{board}/securities/{ticker}/candles.json"
        )
        
        all_data: List[pd.DataFrame] = []
        start = 0
        
        while True:
            params = {
                "from": start_date.strftime("%Y-%m-%d"),
                "till": end_date.strftime("%Y-%m-%d"),
                "interval": interval,
                "start": start,
            }
            
            logger.debug(f"Запрос #{start // self.PAGE_SIZE + 1}: start={start}")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            candles_data = data.get("candles", {})
            columns = candles_data.get("columns", [])
            rows = candles_data.get("data", [])
            
            if not rows:
                logger.info(f"Загрузка завершена на start={start}")
                break
            
            df_chunk = pd.DataFrame(rows, columns=columns)
            all_data.append(df_chunk)
            
            logger.info(f"Загружено {len(rows)} свечей (всего: {sum(len(d) for d in all_data)})")
            
            # Если получили меньше PAGE_SIZE, значит это последняя порция
            if len(rows) < self.PAGE_SIZE:
                break
            
            start += self.PAGE_SIZE
        
        if not all_data:
            return pd.DataFrame()
        
        # Объединяем все части
        df = pd.concat(all_data, ignore_index=True)
        df = self._process_dataframe(df)
        
        return df
    
    def _process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Обработать DataFrame к стандартному формату."""
        
        df = df.rename(columns={"begin": "timestamp"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp")
        df = df.sort_index()
        
        required_cols = ["open", "high", "low", "close", "volume"]
        for col in required_cols:
            if col not in df.columns:
                if col == "volume":
                    df[col] = 0
                else:
                    raise ValueError(f"Отсутствует колонка: {col}")
        
        df = df[required_cols]
        
        for col in required_cols:
            df[col] = df[col].astype(float)
        
        # Удаляем дубликаты
        df = df[~df.index.duplicated(keep='first')]
        
        return df


def load_config(config_path: str = "configs/config.yaml") -> dict:
    """Загрузить конфигурацию из YAML файла."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_provider(config: dict) -> DataProvider:
    """Создать провайдер данных."""
    cache_dir = config.get("data", {}).get("cache_dir", "data")
    return MoexISSProvider(cache_dir=cache_dir)