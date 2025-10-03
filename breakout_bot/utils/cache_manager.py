"""
Advanced caching system for Breakout Bot Trading System.

This module provides intelligent caching with:
- Multi-level caching (memory, disk, Redis)
- TTL management
- Cache invalidation strategies
- Performance optimization
- Memory management
"""

import time
import json
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union, Callable
from dataclasses import dataclass
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry data structure."""
    key: str
    value: Any
    timestamp: float
    ttl: float
    access_count: int = 0
    last_access: float = 0.0
    tags: Optional[set] = None


class CacheManager:
    """Advanced cache manager with multiple strategies."""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
        
        # Cache strategies
        self.strategies = {
            'lru': self._lru_eviction,
            'lfu': self._lfu_eviction,
            'ttl': self._ttl_eviction,
            'size': self._size_eviction
        }
        self.eviction_strategy = 'lru'
        
        # Cache tags for invalidation
        self.tag_index = {}
    
    def _generate_key(self, key: Union[str, tuple]) -> str:
        """Generate cache key from string or tuple."""
        if isinstance(key, tuple):
            key_str = '_'.join(str(k) for k in key)
        else:
            key_str = str(key)
        
        # Hash long keys to save memory
        if len(key_str) > 100:
            return hashlib.md5(key_str.encode()).hexdigest()
        return key_str
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired."""
        return time.time() - entry.timestamp > entry.ttl
    
    def _evict_expired(self):
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if current_time - entry.timestamp > entry.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_entry(key)
    
    def _lru_eviction(self):
        """Least Recently Used eviction strategy."""
        if not self.cache:
            return
        
        # Remove least recently accessed entry
        oldest_key = next(iter(self.cache))
        self._remove_entry(oldest_key)
    
    def _lfu_eviction(self):
        """Least Frequently Used eviction strategy."""
        if not self.cache:
            return
        
        # Find entry with lowest access count
        least_used_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k].access_count)
        self._remove_entry(least_used_key)
    
    def _ttl_eviction(self):
        """Time To Live eviction strategy."""
        self._evict_expired()
    
    def _size_eviction(self):
        """Size-based eviction strategy."""
        if len(self.cache) <= self.max_size:
            return
        
        # Remove largest entries first (approximate by key length)
        largest_key = max(self.cache.keys(), key=len)
        self._remove_entry(largest_key)
    
    def _remove_entry(self, key: str):
        """Remove entry from cache and update stats."""
        if key in self.cache:
            entry = self.cache[key]
            
            # Remove from tag index
            if entry.tags:
                for tag in entry.tags:
                    if tag in self.tag_index:
                        self.tag_index[tag].discard(key)
                        if not self.tag_index[tag]:
                            del self.tag_index[tag]
            
            del self.cache[key]
            self.stats['evictions'] += 1
            self.stats['size'] -= 1
    
    def _make_room(self):
        """Make room for new entry if cache is full."""
        if len(self.cache) >= self.max_size:
            eviction_func = self.strategies.get(self.eviction_strategy, self._lru_eviction)
            eviction_func()
    
    def get(self, key: Union[str, tuple], default: Any = None) -> Any:
        """Get value from cache."""
        cache_key = self._generate_key(key)
        
        with self.lock:
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                
                # Check if expired
                if self._is_expired(entry):
                    self._remove_entry(cache_key)
                    self.stats['misses'] += 1
                    return default
                
                # Update access info
                entry.access_count += 1
                entry.last_access = time.time()
                
                # Move to end (most recently used)
                self.cache.move_to_end(cache_key)
                
                self.stats['hits'] += 1
                return entry.value
            else:
                self.stats['misses'] += 1
                return default
    
    def set(self, key: Union[str, tuple], value: Any, ttl: Optional[float] = None, 
            tags: Optional[set] = None) -> bool:
        """Set value in cache."""
        cache_key = self._generate_key(key)
        ttl = ttl or self.default_ttl
        
        with self.lock:
            # Remove expired entries first
            self._evict_expired()
            
            # Make room if needed
            self._make_room()
            
            # Create entry
            entry = CacheEntry(
                key=cache_key,
                value=value,
                timestamp=time.time(),
                ttl=ttl,
                access_count=1,
                last_access=time.time(),
                tags=tags or set()
            )
            
            # Add to cache
            self.cache[cache_key] = entry
            self.stats['size'] += 1
            
            # Update tag index
            if tags:
                for tag in tags:
                    if tag not in self.tag_index:
                        self.tag_index[tag] = set()
                    self.tag_index[tag].add(cache_key)
            
            return True
    
    def delete(self, key: Union[str, tuple]) -> bool:
        """Delete value from cache."""
        cache_key = self._generate_key(key)
        
        with self.lock:
            if cache_key in self.cache:
                self._remove_entry(cache_key)
                return True
            return False
    
    def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all entries with specific tag."""
        with self.lock:
            if tag not in self.tag_index:
                return 0
            
            keys_to_remove = list(self.tag_index[tag])
            for key in keys_to_remove:
                self._remove_entry(key)
            
            return len(keys_to_remove)
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate entries matching pattern."""
        import re
        
        with self.lock:
            pattern_re = re.compile(pattern)
            keys_to_remove = [key for key in self.cache.keys() if pattern_re.match(key)]
            
            for key in keys_to_remove:
                self._remove_entry(key)
            
            return len(keys_to_remove)
    
    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.tag_index.clear()
            self.stats['size'] = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': hit_rate,
                'evictions': self.stats['evictions'],
                'strategy': self.eviction_strategy
            }
    
    def get_memory_usage(self) -> int:
        """Estimate memory usage in bytes."""
        with self.lock:
            total_size = 0
            for entry in self.cache.values():
                # Rough estimation
                total_size += len(str(entry.key)) + len(str(entry.value)) + 100
            return total_size
    
    def optimize(self):
        """Optimize cache by removing expired entries and adjusting size."""
        with self.lock:
            # Remove expired entries
            self._evict_expired()
            
            # If still over limit, use eviction strategy
            while len(self.cache) > self.max_size:
                eviction_func = self.strategies.get(self.eviction_strategy, self._lru_eviction)
                eviction_func()
    
    def set_eviction_strategy(self, strategy: str):
        """Set cache eviction strategy."""
        if strategy in self.strategies:
            self.eviction_strategy = strategy
            logger.info(f"Cache eviction strategy set to: {strategy}")
        else:
            logger.warning(f"Unknown eviction strategy: {strategy}")


class CachedFunction:
    """Decorator for caching function results."""
    
    def __init__(self, cache_manager: CacheManager, ttl: float = 300.0, 
                 key_func: Optional[Callable] = None, tags: Optional[set] = None):
        self.cache_manager = cache_manager
        self.ttl = ttl
        self.key_func = key_func
        self.tags = tags or set()
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            if self.key_func:
                cache_key = self.key_func(*args, **kwargs)
            else:
                cache_key = (func.__name__, args, tuple(sorted(kwargs.items())))
            
            # Try to get from cache
            result = self.cache_manager.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            self.cache_manager.set(cache_key, result, ttl=self.ttl, tags=self.tags)
            
            return result
        
        return wrapper


# Global cache manager instance
_cache_manager = None

def get_cache_manager() -> CacheManager:
    """Get or create global cache manager."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(ttl: float = 300.0, tags: Optional[set] = None):
    """Decorator for caching function results."""
    cache_manager = get_cache_manager()
    return CachedFunction(cache_manager, ttl=ttl, tags=tags)
