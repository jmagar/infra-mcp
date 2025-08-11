"""
Glances HTTP Client

Low-level HTTP client for Glances API communication with connection pooling,
error handling, and authentication support.
"""

import asyncio
from contextlib import asynccontextmanager
import logging
from typing import Any, AsyncGenerator

import httpx
from apps.backend.src.core.config import get_settings

logger = logging.getLogger(__name__)


class GlancesClient:
    """HTTP client for Glances API with connection pooling and error handling"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers={"Accept": "application/json"}
        )
    
    async def get_endpoint(self, endpoint: str) -> dict[str, Any]:
        """Get data from a single Glances API endpoint"""
        try:
            endpoint = endpoint.lstrip('/')
            url = f"/api/4/{endpoint}"
            
            logger.debug(f"Making request to {self.base_url}{url}")
            response = await self.client.get(url)
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {str(e)}")
            raise
    
    async def get_multiple_endpoints(self, endpoints: list[str]) -> dict[str, dict[str, Any]]:
        """Get data from multiple endpoints in parallel"""
        tasks = []
        for endpoint in endpoints:
            task = asyncio.create_task(
                self.get_endpoint(endpoint),
                name=f"glances_{endpoint}"
            )
            tasks.append((endpoint, task))
        
        results = {}
        for endpoint, task in tasks:
            try:
                results[endpoint] = await task
            except Exception as e:
                logger.error(f"Failed to get data from {endpoint}: {str(e)}")
                results[endpoint] = None
        
        return results
    
    async def test_connectivity(self) -> bool:
        """Test if Glances server is accessible"""
        try:
            response = await self.client.get("/api/4/status")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Glances connectivity test failed: {str(e)}")
            return False
    
    async def close(self) -> None:
        """Close HTTP client connections"""
        await self.client.aclose()
    
    @asynccontextmanager
    async def request_context(self) -> AsyncGenerator[httpx.AsyncClient, None]:
        """Context manager for HTTP requests with automatic cleanup"""
        try:
            yield self.client
        finally:
            # Client cleanup is handled by the main close() method
            pass


def get_glances_client(device_url: str) -> GlancesClient:
    """Get Glances client instance for device"""
    settings = get_settings()
    timeout = getattr(settings.glances, 'connection_timeout', 30)
    return GlancesClient(device_url, timeout=timeout)