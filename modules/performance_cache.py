"""
Performance caching and optimization utilities for TerraVision.

This module provides caching mechanisms to improve performance for large
Terraform projects by avoiding redundant computations.
"""

import functools
import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional, Callable, Tuple
from pathlib import Path


logger = logging.getLogger(__name__)


class ResourceCache:
    """Cache for resource metadata and processing results."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize the cache.
        
        Args:
            max_size: Maximum number of cached items
            ttl_seconds: Time to live for cached items in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._access_order: Dict[str, float] = {}
        
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache if it exists and hasn't expired."""
        if key not in self._cache:
            return None
            
        value, timestamp = self._cache[key]
        
        # Check if expired
        if time.time() - timestamp > self.ttl_seconds:
            self._remove(key)
            return None
            
        # Update access time
        self._access_order[key] = time.time()
        logger.debug(f"Cache hit for key: {key}")
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in cache, evicting old items if necessary."""
        # Remove expired items first
        self._cleanup_expired()
        
        # Evict LRU items if cache is full
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_lru()
        
        self._cache[key] = (value, time.time())
        self._access_order[key] = time.time()
        logger.debug(f"Cache set for key: {key}")
    
    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()
        self._access_order.clear()
        logger.debug("Cache cleared")
    
    def _remove(self, key: str) -> None:
        """Remove a key from cache."""
        self._cache.pop(key, None)
        self._access_order.pop(key, None)
    
    def _cleanup_expired(self) -> None:
        """Remove expired items from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp > self.ttl_seconds
        ]
        
        for key in expired_keys:
            self._remove(key)
            logger.debug(f"Removed expired cache entry: {key}")
    
    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self._access_order:
            return
            
        lru_key = min(self._access_order.keys(), key=lambda k: self._access_order[k])
        self._remove(lru_key)
        logger.debug(f"Evicted LRU cache entry: {lru_key}")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds
        }


# Global cache instances
_resource_cache = ResourceCache()
_relationship_cache = ResourceCache(max_size=500, ttl_seconds=1800)


def cache_result(cache_instance: ResourceCache = None, key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        cache_instance: Cache instance to use (default: global resource cache)
        key_prefix: Prefix for cache keys
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = cache_instance or _resource_cache
            
            # Generate cache key from function name and arguments
            key_data = {
                "function": func.__name__,
                "args": str(args),
                "kwargs": sorted(kwargs.items())
            }
            key_hash = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
            cache_key = f"{key_prefix}{func.__name__}_{key_hash}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Compute result and cache it
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            cache.set(cache_key, result)
            logger.debug(f"Cached result for {func.__name__} (execution time: {execution_time:.3f}s)")
            
            return result
        
        return wrapper
    return decorator


def cache_resource_metadata(func: Callable) -> Callable:
    """Decorator specifically for caching resource metadata operations."""
    return cache_result(_resource_cache, "metadata_")(func)


def cache_relationships(func: Callable) -> Callable:
    """Decorator specifically for caching relationship calculations."""
    return cache_result(_relationship_cache, "relationships_")(func)


class PerformanceProfiler:
    """Simple performance profiler for identifying bottlenecks."""
    
    def __init__(self):
        self.timings: Dict[str, list] = {}
        self.call_counts: Dict[str, int] = {}
    
    def time_function(self, func_name: str):
        """Decorator to time function execution."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                if func_name not in self.timings:
                    self.timings[func_name] = []
                    self.call_counts[func_name] = 0
                
                self.timings[func_name].append(execution_time)
                self.call_counts[func_name] += 1
                
                return result
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics."""
        stats = {}
        
        for func_name, times in self.timings.items():
            stats[func_name] = {
                "call_count": self.call_counts[func_name],
                "total_time": sum(times),
                "average_time": sum(times) / len(times),
                "min_time": min(times),
                "max_time": max(times)
            }
        
        return stats
    
    def log_stats(self) -> None:
        """Log performance statistics."""
        stats = self.get_stats()
        
        logger.info("Performance Statistics:")
        for func_name, data in sorted(stats.items(), key=lambda x: x[1]["total_time"], reverse=True):
            logger.info(
                f"  {func_name}: {data['call_count']} calls, "
                f"{data['total_time']:.3f}s total, "
                f"{data['average_time']:.3f}s avg"
            )


# Global profiler instance
_profiler = PerformanceProfiler()


def profile_performance(func_name: str = None):
    """Decorator to profile function performance."""
    def decorator(func):
        name = func_name or f"{func.__module__}.{func.__name__}"
        return _profiler.time_function(name)(func)
    return decorator


class LazyLoader:
    """Lazy loader for expensive resources."""
    
    def __init__(self, loader_func: Callable, *args, **kwargs):
        """
        Initialize lazy loader.
        
        Args:
            loader_func: Function to call when resource is needed
            *args, **kwargs: Arguments to pass to loader function
        """
        self.loader_func = loader_func
        self.args = args
        self.kwargs = kwargs
        self._loaded = False
        self._value = None
    
    def get(self):
        """Get the loaded value, loading it if necessary."""
        if not self._loaded:
            logger.debug(f"Lazy loading: {self.loader_func.__name__}")
            self._value = self.loader_func(*self.args, **self.kwargs)
            self._loaded = True
        
        return self._value
    
    def is_loaded(self) -> bool:
        """Check if the value has been loaded."""
        return self._loaded


def memoize_with_size_limit(max_size: int = 128):
    """
    Memoization decorator with size limit.
    
    Args:
        max_size: Maximum number of cached results
    """
    def decorator(func):
        cache = {}
        access_order = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create key from arguments
            key = str(args) + str(sorted(kwargs.items()))
            
            if key in cache:
                access_order[key] = time.time()
                return cache[key]
            
            # Evict oldest if cache is full
            if len(cache) >= max_size:
                oldest_key = min(access_order.keys(), key=lambda k: access_order[k])
                del cache[oldest_key]
                del access_order[oldest_key]
            
            # Compute and cache result
            result = func(*args, **kwargs)
            cache[key] = result
            access_order[key] = time.time()
            
            return result
        
        return wrapper
    return decorator


def clear_all_caches() -> None:
    """Clear all performance caches."""
    _resource_cache.clear()
    _relationship_cache.clear()
    logger.info("All caches cleared")


def get_cache_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all caches."""
    return {
        "resource_cache": _resource_cache.stats(),
        "relationship_cache": _relationship_cache.stats()
    }


def get_performance_stats() -> Dict[str, Dict[str, float]]:
    """Get performance profiling statistics."""
    return _profiler.get_stats()


def log_performance_summary() -> None:
    """Log a summary of performance statistics."""
    _profiler.log_stats()
    
    cache_stats = get_cache_stats()
    logger.info("Cache Statistics:")
    for cache_name, stats in cache_stats.items():
        logger.info(f"  {cache_name}: {stats['size']}/{stats['max_size']} items")
