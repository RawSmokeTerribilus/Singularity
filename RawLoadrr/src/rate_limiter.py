# -*- coding: utf-8 -*-
"""
Rate Limiter for API calls

Implements per-tracker rate limiting to prevent API abuse
and respect rate limit constraints.
"""
import asyncio
import time
from typing import Dict
from src.console import console


class AsyncRateLimiter:
    """
    Async rate limiter that respects API call limits per minute.
    
    Per-tracker configuration:
    - Each tracker has its own rate limit window
    - Non-blocking: waits transparently without halting other operations
    - Thread-safe for async contexts
    
    Example:
        limiter = AsyncRateLimiter()
        await limiter.acquire('MILNU')  # Waits if needed, respects 30 calls/min
        # Make API call
    """
    
    def __init__(self):
        """Initialize rate limiter with default configs"""
        self.tracker_limits: Dict[str, int] = {
            'MILNU': 30,      # 30 calls per minute
            'EMU': 60,        # 60 calls per minute (default for others)
            'AITHER': 60,
            'ANT': 60,
            'ACM': 60,
            'BHD': 60,
            'BLU': 60,
            'CBR': 60,
            'FNP': 60,
            'HHD': 60,
            'HUNO': 60,
            'ITA': 60,
            'JPTV': 60,
            'LCD': 60,
            'LDU': 60,
            'LST': 60,
            'LT': 60,
            'MB': 60,
            'NBL': 60,
            'OE': 60,
            'OINK': 60,
            'OTW': 60,
            'PSS': 60,
            'PTT': 60,
            'RF': 60,
            'R4E': 60,
            'RHD': 60,
            'RTF': 60,
            'SHRI': 60,
            'SN': 60,
            'SP': 60,
            'TLZ': 60,
            'TTR': 60,
            'TOCA': 60,
            'ULCX': 60,
            'UTP': 60,
            'YU': 60,
        }
        
        # Track API calls per tracker: {tracker: [timestamps]}
        self.call_history: Dict[str, list] = {}
        self.window = 60  # seconds
        self.verbose = False
    
    async def acquire(self, tracker: str) -> float:
        """
        Acquire token for API call. Blocks if rate limit would be exceeded.
        
        Args:
            tracker: Tracker identifier (e.g., 'MILNU', 'EMU')
            
        Returns:
            float: Wait time in seconds (0 if no wait needed)
        """
        if tracker not in self.call_history:
            self.call_history[tracker] = []
        
        max_calls = self.tracker_limits.get(tracker, 60)
        current_time = time.time()
        
        # Remove old calls outside the window
        self.call_history[tracker] = [
            t for t in self.call_history[tracker]
            if current_time - t < self.window
        ]
        
        # Check if we need to wait
        if len(self.call_history[tracker]) >= max_calls:
            # Calculate wait time
            oldest_call = self.call_history[tracker][0]
            wait_time = (oldest_call + self.window) - current_time
            wait_time = max(0, wait_time)
            
            if wait_time > 0:
                if self.verbose:
                    console.print(
                        f"[yellow]Rate limit hit for {tracker}: "
                        f"waiting {wait_time:.2f}s ({len(self.call_history[tracker])}/{max_calls} calls)[/yellow]"
                    )
                await asyncio.sleep(wait_time)
        
        # Record this call
        self.call_history[tracker].append(time.time())
        
        wait_time = 0
        if self.verbose:
            console.print(
                f"[cyan]API call acquired for {tracker} "
                f"({len(self.call_history[tracker])}/{max_calls})[/cyan]"
            )
        
        return wait_time
    
    def set_tracker_limit(self, tracker: str, calls_per_minute: int):
        """
        Update rate limit for a specific tracker.
        
        Args:
            tracker: Tracker identifier
            calls_per_minute: New limit
        """
        self.tracker_limits[tracker] = calls_per_minute
        if self.verbose:
            console.print(
                f"[blue]Rate limit updated: {tracker} = {calls_per_minute} calls/min[/blue]"
            )
    
    def reset(self, tracker: str = None):
        """
        Reset call history for a tracker or all trackers.
        
        Args:
            tracker: Tracker to reset, or None for all
        """
        if tracker:
            if tracker in self.call_history:
                self.call_history[tracker] = []
        else:
            self.call_history = {}
    
    def get_stats(self, tracker: str) -> Dict:
        """
        Get current rate limit statistics for a tracker.
        
        Returns:
            Dict with current calls, max calls, time to reset
        """
        if tracker not in self.call_history:
            return {
                'current_calls': 0,
                'max_calls': self.tracker_limits.get(tracker, 60),
                'time_to_reset': 0,
                'window': self.window
            }
        
        current_time = time.time()
        calls = [t for t in self.call_history[tracker] if current_time - t < self.window]
        
        time_to_reset = 0
        if calls:
            time_to_reset = (calls[0] + self.window) - current_time
            time_to_reset = max(0, time_to_reset)
        
        return {
            'current_calls': len(calls),
            'max_calls': self.tracker_limits.get(tracker, 60),
            'time_to_reset': time_to_reset,
            'window': self.window
        }


# Global rate limiter instance
rate_limiter = AsyncRateLimiter()
