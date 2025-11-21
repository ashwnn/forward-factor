"""Polygon.io option chain provider implementation."""
import httpx
from datetime import datetime, date
from typing import List, Optional
from app.providers import OptionChainProvider, ProviderError
from app.providers.models import ChainSnapshot, Expiry, Contract
from app.core.config import settings


class PolygonProvider(OptionChainProvider):
    """Polygon.io implementation of option chain provider."""
    
    BASE_URL = "https://api.polygon.io"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.polygon_api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_chain_snapshot(self, ticker: str) -> ChainSnapshot:
        """
        Fetch option chain snapshot from Polygon.io.
        
        Uses the options chain snapshot endpoint to get all contracts.
        """
        try:
            # Get underlying price first
            underlying_price = await self._get_underlying_price(ticker)
            
            # Get option chain
            url = f"{self.BASE_URL}/v3/snapshot/options/{ticker}"
            params = {"apiKey": self.api_key}
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "OK":
                raise ProviderError(f"Polygon API returned status: {data.get('status')}")
            
            # Parse contracts
            contracts = self._parse_contracts(data.get("results", []))
            
            # Group by expiry
            expiries = self._group_by_expiry(contracts)
            
            return ChainSnapshot(
                ticker=ticker,
                as_of=datetime.utcnow(),
                underlying_price=underlying_price,
                expiries=expiries,
                provider="polygon"
            )
            
        except httpx.HTTPError as e:
            raise ProviderError(f"Polygon API error: {str(e)}")
        except Exception as e:
            raise ProviderError(f"Unexpected error: {str(e)}")
    
    async def _get_underlying_price(self, ticker: str) -> float:
        """Get current underlying stock price."""
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
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
