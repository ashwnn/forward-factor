"""Abstract interface for option chain providers."""
from abc import ABC, abstractmethod
from app.providers.models import ChainSnapshot


class OptionChainProvider(ABC):
    """Abstract base class for option chain data providers."""
    
    @abstractmethod
    async def get_chain_snapshot(self, ticker: str) -> ChainSnapshot:
        """
        Fetch option chain snapshot for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            ChainSnapshot with all expiries and contracts
            
        Raises:
            ProviderError: If API call fails
        """
        pass


class ProviderError(Exception):
    """Exception raised when provider API fails."""
    pass
