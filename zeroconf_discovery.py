"""Zeroconf discovery for PipePlay service."""

import asyncio
import logging
import socket
from typing import Optional
from zeroconf import ServiceInfo, Zeroconf
from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf

_LOGGER = logging.getLogger(__name__)


class PipePlayZeroconfService:
    """Handle Zeroconf service registration for automatic discovery."""
    
    def __init__(self, name: str, port: int, host: str = None):
        """Initialize Zeroconf service."""
        self._name = name
        self._port = port
        self._host = host or self._get_local_ip()
        self._zeroconf: Optional[AsyncZeroconf] = None
        self._service_info: Optional[AsyncServiceInfo] = None
    
    def _get_local_ip(self) -> str:
        """Get the local IP address."""
        try:
            # Connect to a remote host to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    async def start(self):
        """Start Zeroconf service registration."""
        try:
            self._zeroconf = AsyncZeroconf()
            
            # Create service info
            service_type = "_pipeplay._tcp.local."
            service_name = f"{self._name}.{service_type}"
            
            # Convert host to bytes if needed
            if isinstance(self._host, str):
                addresses = [socket.inet_aton(self._host)]
            else:
                addresses = [self._host]
            
            properties = {
                "version": "0.1.0",
                "service": "pipeplay",
                "api_version": "1.0",
                "name": self._name,
            }
            
            # Convert properties to bytes
            properties_bytes = {
                key.encode('utf-8'): value.encode('utf-8') if isinstance(value, str) else value
                for key, value in properties.items()
            }
            
            self._service_info = AsyncServiceInfo(
                service_type,
                service_name,
                addresses=addresses,
                port=self._port,
                properties=properties_bytes,
                server=f"{socket.gethostname()}.local.",
            )
            
            await self._zeroconf.async_register_service(self._service_info)
            _LOGGER.info(f"Zeroconf service registered: {service_name} on {self._host}:{self._port}")
            
        except Exception as e:
            _LOGGER.error(f"Failed to start Zeroconf service: {e}")
    
    async def stop(self):
        """Stop Zeroconf service registration."""
        try:
            if self._service_info and self._zeroconf:
                await self._zeroconf.async_unregister_service(self._service_info)
                await self._zeroconf.async_close()
                _LOGGER.info("Zeroconf service unregistered")
                
        except Exception as e:
            _LOGGER.error(f"Error stopping Zeroconf service: {e}")
    
    @property
    def service_name(self) -> str:
        """Get the full service name."""
        return f"{self._name}._pipeplay._tcp.local."


class PipePlayZeroconfDiscovery:
    """Discovery client for finding PipePlay services."""
    
    def __init__(self):
        """Initialize discovery client."""
        self._zeroconf: Optional[AsyncZeroconf] = None
    
    async def discover_services(self, timeout: float = 10.0) -> list:
        """Discover PipePlay services on the network."""
        services = []
        
        try:
            self._zeroconf = AsyncZeroconf()
            
            from zeroconf.asyncio import AsyncServiceBrowser
            from zeroconf import ServiceListener
            
            class PipePlayServiceListener(ServiceListener):
                def __init__(self):
                    self.services = []
                
                def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                    info = zc.get_service_info(type_, name)
                    if info:
                        # Extract host and port
                        host = socket.inet_ntoa(info.addresses[0]) if info.addresses else None
                        port = info.port
                        
                        # Extract properties
                        properties = {}
                        if info.properties:
                            for key, value in info.properties.items():
                                properties[key.decode('utf-8')] = value.decode('utf-8')
                        
                        service_info = {
                            "name": name,
                            "host": host,
                            "port": port,
                            "properties": properties,
                        }
                        self.services.append(service_info)
                        _LOGGER.info(f"Discovered PipePlay service: {service_info}")
                
                def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                    _LOGGER.info(f"PipePlay service removed: {name}")
                
                def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                    _LOGGER.info(f"PipePlay service updated: {name}")
            
            listener = PipePlayServiceListener()
            browser = AsyncServiceBrowser(self._zeroconf.zeroconf, "_pipeplay._tcp.local.", listener)
            
            # Wait for discovery
            await asyncio.sleep(timeout)
            
            # Stop browser
            browser.cancel()
            services = listener.services
            
        except Exception as e:
            _LOGGER.error(f"Error during service discovery: {e}")
        finally:
            if self._zeroconf:
                await self._zeroconf.async_close()
        
        return services