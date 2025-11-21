"""Massive.com option chain provider stub."""
from app.providers import OptionChainProvider, ProviderError
from app.providers.models import ChainSnapshot


class MassiveProvider(OptionChainProvider):
    """Massive.com implementation (stub for future implementation)."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
    
    async def get_chain_snapshot(self, ticker: str) -> ChainSnapshot:
        """Fetch option chain snapshot from Massive.com."""
        raise ProviderError("Massive provider not yet implemented")
