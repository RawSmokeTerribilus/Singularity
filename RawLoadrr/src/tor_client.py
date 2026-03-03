# -*- coding: utf-8 -*-
"""
Tor SOCKS5 Client Module

Provides transparent Tor fallback for API calls when direct connection fails.
Automatically retries failed requests through Tor SOCKS proxy.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from socks import socksocket, SOCKS5
import socket
from typing import Optional, Tuple
from src.console import console
import logging


class TorSession:
    """
    Hybrid HTTP session with automatic Tor fallback.
    
    First attempts direct connection, then falls back to Tor SOCKS5 on failure.
    """
    
    def __init__(self, tor_socks_port: int = 9050, logger=None):
        """
        Initialize Tor-capable session.
        
        Args:
            tor_socks_port: SOCKS5 proxy port (default: 9050)
            logger: Optional logger instance
        """
        self.tor_socks_port = tor_socks_port
        self.tor_socks_host = '127.0.0.1'
        self.logger = logger
        self.tor_connected = False
        
        # Create regular session
        self.session = requests.Session()
        
        # Check if Tor is available
        self._check_tor_available()
    
    def _check_tor_available(self) -> bool:
        """Check if Tor SOCKS5 is available"""
        try:
            sock = socksocket(socket.AF_INET, socket.SOCK_STREAM)
            sock.set_proxy(SOCKS5, self.tor_socks_host, self.tor_socks_port)
            sock.connect(("check.torproject.org", 80))
            sock.close()
            self.tor_connected = True
            if self.logger:
                self.logger.debug("✓ Tor SOCKS5 available on port 9050")
            console.print("[green]✓ Tor SOCKS5 available[/green]")
            return True
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Tor SOCKS5 not available: {str(e)}")
            console.print(f"[yellow]⚠ Tor not available: {str(e)}")
            self.tor_connected = False
            return False
    
    def _create_tor_session(self) -> requests.Session:
        """Create session that routes through Tor SOCKS5"""
        host = self.tor_socks_host
        port = self.tor_socks_port
        
        class TorHTTPAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                kwargs['_socks_options'] = (SOCKS5, host, port)
                return super().init_poolmanager(*args, **kwargs)
        
        session = requests.Session()
        session.mount('http://', TorHTTPAdapter())
        session.mount('https://', TorHTTPAdapter())
        return session
    
    def get(self, url: str, use_tor: bool = False, **kwargs) -> requests.Response:
        """
        GET request with optional Tor fallback.
        
        Args:
            url: URL to request
            use_tor: Force Tor connection
            **kwargs: Additional arguments to requests.get
            
        Returns:
            requests.Response object
        """
        if use_tor and self.tor_connected:
            if self.logger:
                self.logger.debug(f"GET {url} via Tor")
            console.print(f"[cyan]→ Via Tor:[/cyan] {url}")
            tor_session = self._create_tor_session()
            return tor_session.get(url, **kwargs)
        else:
            if self.logger:
                self.logger.debug(f"GET {url} (direct)")
            return self.session.get(url, **kwargs)
    
    def post(self, url: str, use_tor: bool = False, **kwargs) -> requests.Response:
        """
        POST request with optional Tor fallback.
        
        Args:
            url: URL to request
            use_tor: Force Tor connection
            **kwargs: Additional arguments to requests.post
            
        Returns:
            requests.Response object
        """
        if use_tor and self.tor_connected:
            if self.logger:
                self.logger.debug(f"POST {url} via Tor")
            console.print(f"[cyan]→ Via Tor:[/cyan] {url}")
            tor_session = self._create_tor_session()
            return tor_session.post(url, **kwargs)
        else:
            if self.logger:
                self.logger.debug(f"POST {url} (direct)")
            return self.session.post(url, **kwargs)
    
    def close(self):
        """Close sessions"""
        self.session.close()


class TorFallbackMixin:
    """
    Mixin to add Tor fallback capability to tracker classes.
    
    Usage:
        class MyTracker(TorFallbackMixin):
            async def upload(self, meta):
                response = await self.request_with_fallback(
                    method='post',
                    url=self.upload_url,
                    files=files,
                    data=data
                )
    """
    
    def __init__(self):
        self.tor_session = None
    
    async def _initialize_tor(self):
        """Initialize Tor session if not already done"""
        if self.tor_session is None:
            logger = getattr(self, 'logger', None)
            self.tor_session = TorSession(logger=logger)
    
    async def request_with_fallback(
        self,
        method: str = 'get',
        url: str = '',
        fallback_on_codes: list = None,
        use_tor: bool = False,
        **kwargs
    ) -> Tuple[Optional[requests.Response], bool]:
        """
        Make request with automatic Tor fallback on failure.
        
        Args:
            method: 'get' or 'post'
            url: URL to request
            fallback_on_codes: HTTP status codes to trigger fallback (default: [403, 408, 500, 502, 503, 504])
            use_tor: Force Tor from start
            **kwargs: Arguments to pass to requests method
            
        Returns:
            Tuple of (response, used_tor) or (None, False) on error
        """
        if fallback_on_codes is None:
            fallback_on_codes = [403, 408, 500, 502, 503, 504]
        
        await self._initialize_tor()
        
        # First attempt: direct connection (unless forced to Tor)
        if not use_tor:
            try:
                method_func = getattr(self.tor_session, method)
                response = method_func(url, use_tor=False, **kwargs)
                
                # Check if response indicates blocking
                if response.status_code not in fallback_on_codes:
                    return response, False
                
                # Status code suggests blocking, try Tor
                if self.logger:
                    self.logger.warning(
                        f"Got HTTP {response.status_code} - trying Tor fallback"
                    )
                console.print(
                    f"[yellow]HTTP {response.status_code} - attempting Tor fallback...[/yellow]"
                )
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Direct connection failed: {str(e)}")
                console.print(
                    f"[yellow]Connection failed ({type(e).__name__}) - trying Tor fallback...[/yellow]"
                )
        
        # Fallback: try via Tor
        if self.tor_session.tor_connected:
            try:
                if self.logger:
                    self.logger.debug(f"Attempting {method.upper()} via Tor")
                
                method_func = getattr(self.tor_session, method)
                response = method_func(url, use_tor=True, **kwargs)
                
                if self.logger:
                    self.logger.info(f"Successfully connected via Tor (HTTP {response.status_code})")
                
                console.print(
                    f"[green]✓ Connected via Tor (HTTP {response.status_code})[/green]"
                )
                return response, True
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Tor connection also failed: {str(e)}")
                console.print(
                    f"[red]✗ Tor connection failed: {str(e)}[/red]"
                )
                return None, False
        else:
            if self.logger:
                self.logger.error("Tor not available for fallback")
            console.print(
                "[red]✗ Tor not available and direct connection failed[/red]"
            )
            return None, False
    
    def close_tor(self):
        """Close Tor session"""
        if self.tor_session:
            self.tor_session.close()
