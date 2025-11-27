"""Polygon.io option chain provider implementation."""
import httpx
from datetime import datetime, date, timezone, timedelta
from typing import List, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging
from app.providers import OptionChainProvider, ProviderError
from app.providers.models import ChainSnapshot, Expiry, Contract
from app.core.config import settings


logger = logging.getLogger(__name__)


class PolygonProvider(OptionChainProvider):
    """Polygon.io implementation of option chain provider."""
    
    BASE_URL = "https://api.polygon.io"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.polygon_api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _make_request(self, url: str, params: dict) -> dict:
        """Make HTTP request with retry logic for transient failures.
        
        Retries up to 3 times with exponential backoff for:
        - Timeout errors
        - Connection errors
        
        Does NOT retry for:
        - HTTP errors (4xx, 5xx) - those need different handling
        """
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_chain_snapshot(self, ticker: str) -> ChainSnapshot:
        """
        Fetch option chain snapshot from Polygon.io.
        
        Uses the options chain snapshot endpoint to get all contracts.
        Includes retry logic for transient network failures.
        """
        try:
            # Get underlying price first
            underlying_price = await self._get_underlying_price(ticker)
            
            # Get option chain
            url = f"{self.BASE_URL}/v3/snapshot/options/{ticker}"
            params = {"apiKey": self.api_key}
            
            data = await self._make_request(url, params)
            
            if data.get("status") != "OK":
                raise ProviderError(f"Polygon API returned status: {data.get('status')}")
            
            # Parse contracts
            contracts = self._parse_contracts(data.get("results", []))
            
            # Group by expiry
            expiries = self._group_by_expiry(contracts)
            
            return ChainSnapshot(
                ticker=ticker,
                as_of=datetime.now(timezone.utc),
                underlying_price=underlying_price,
                expiries=expiries,
                provider="polygon"
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise ProviderError(
                    "Polygon API Access Denied (403): Your API key does not support the 'Universal Snapshot' endpoint. "
                    "This feature requires a paid subscription (e.g., Starter or Developer plan) that includes Real-time Options data. "
                    "Please upgrade your plan at https://polygon.io/pricing"
                )
            elif e.response.status_code == 429:
                raise ProviderError(
                    "Polygon API rate limit exceeded (429). Please wait before making more requests."
                )
            raise ProviderError(f"Polygon API error: {str(e)}")
        except httpx.TimeoutException as e:
            raise ProviderError(f"Polygon API timeout after retries: {str(e)}")
        except httpx.HTTPError as e:
            raise ProviderError(f"Polygon API connection error: {str(e)}")
        except Exception as e:
            raise ProviderError(f"Unexpected error: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _get_underlying_price(self, ticker: str) -> float:
        """Get current underlying stock price with retry logic."""
        url = f"{self.BASE_URL}/v2/aggs/ticker/{ticker}/prev"
        params = {"apiKey": self.api_key}
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("results"):
            raise ProviderError(f"No price data for {ticker}")
        
        return data["results"][0]["c"]  # Close price
    
    def _parse_contracts(self, results: List[dict]) -> List[Contract]:
        """Parse Polygon contract data into Contract objects."""
        contracts = []
        
        for item in results:
            details = item.get("details", {})
            greeks = item.get("greeks", {})
            quote = item.get("last_quote", {})
            day = item.get("day", {})
            
            # Parse expiry date
            expiry_str = details.get("expiration_date")
            if not expiry_str:
                continue
            
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            
            contract = Contract(
                symbol=details.get("ticker", ""),
                strike=details.get("strike_price", 0.0),
                expiry=expiry_date,
                option_type="call" if details.get("contract_type") == "call" else "put",
                bid=quote.get("bid"),
                ask=quote.get("ask"),
                last=item.get("last_trade", {}).get("price"),
                volume=day.get("volume"),
                open_interest=item.get("open_interest"),
                implied_volatility=greeks.get("implied_volatility"),
                delta=greeks.get("delta"),
                gamma=greeks.get("gamma"),
                theta=greeks.get("theta"),
                vega=greeks.get("vega")
            )
            
            contracts.append(contract)
        
        return contracts
    
    def _group_by_expiry(self, contracts: List[Contract]) -> List[Expiry]:
        """Group contracts by expiry date."""
        expiry_map = {}
        
        for contract in contracts:
            if contract.expiry not in expiry_map:
                expiry_map[contract.expiry] = []
            expiry_map[contract.expiry].append(contract)
        
        expiries = []
        today = date.today()
        
        for expiry_date, expiry_contracts in sorted(expiry_map.items()):
            dte = (expiry_date - today).days
            expiries.append(Expiry(
                expiry_date=expiry_date,
                dte=dte,
                contracts=expiry_contracts
            ))
        
        return expiries
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def get_top_liquid_tickers(self, limit: int = 100) -> List[str]:
        """
        Get top liquid optionable stock tickers by dollar volume.
        
        Uses the grouped daily aggregates endpoint to fetch market-wide data
        and returns the top N tickers sorted by dollar volume (price * volume).
        
        Args:
            limit: Number of top tickers to return (default 100)
            
        Returns:
            List of ticker symbols sorted by liquidity
            
        Raises:
            ProviderError: If API call fails
        """
        try:
            # Use yesterday's date to ensure data is available
            target_date = date.today() - timedelta(days=1)
            # Skip weekends
            while target_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                target_date -= timedelta(days=1)
            
            url = f"{self.BASE_URL}/v2/aggs/grouped/locale/us/market/stocks/{target_date.strftime('%Y-%m-%d')}"
            params = {
                "apiKey": self.api_key,
                "adjusted": "true"
            }
            
            data = await self._make_request(url, params)
            
            if data.get("status") != "OK":
                raise ProviderError(f"Polygon API returned status: {data.get('status')}")
            
            results = data.get("results", [])
            
            if not results:
                logger.warning("No results from grouped daily aggregates")
                return []
            
            # Filter and calculate dollar volume
            ticker_volumes = []
            for item in results:
                ticker = item.get("T", "")  # Ticker symbol
                close_price = item.get("c", 0)  # Close price
                volume = item.get("v", 0)  # Volume
                
                # Skip if missing data or invalid values
                if not ticker or not close_price or not volume:
                    continue
                
                # Skip non-standard tickers (those with special characters)
                if not ticker.isalpha() or len(ticker) > 5:
                    continue
                
                # Calculate dollar volume
                dollar_volume = close_price * volume
                ticker_volumes.append((ticker, dollar_volume))
            
            # Sort by dollar volume (descending) and take top N
            ticker_volumes.sort(key=lambda x: x[1], reverse=True)
            top_tickers = [t[0] for t in ticker_volumes[:limit]]
            
            logger.info(f"Retrieved {len(top_tickers)} top liquid tickers")
            return top_tickers
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise ProviderError(
                    "Polygon API Access Denied (403): Your API key does not have access to grouped daily aggregates."
                )
            elif e.response.status_code == 429:
                raise ProviderError(
                    "Polygon API rate limit exceeded (429). Please wait before making more requests."
                )
            raise ProviderError(f"Polygon API error: {str(e)}")
        except httpx.TimeoutException as e:
            raise ProviderError(f"Polygon API timeout after retries: {str(e)}")
        except httpx.HTTPError as e:
            raise ProviderError(f"Polygon API connection error: {str(e)}")
        except Exception as e:
            raise ProviderError(f"Unexpected error fetching top liquid tickers: {str(e)}")
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
