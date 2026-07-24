"""
Thumbnail caching system for efficient image loading.
Implements LRU cache with disk persistence.
"""

import time
import threading
from pathlib import Path
from typing import Optional, Dict
import hashlib
import requests
from PIL import Image
from io import BytesIO


class ThumbnailCache:
    """
    Thread-safe thumbnail cache with memory and optional disk caching.
    """
    
    _instance: Optional['ThumbnailCache'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'ThumbnailCache':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._memory_cache: Dict[str, Image.Image] = {}
        self._session: Optional[requests.Session] = None
        self._cache_dir: Optional[Path] = None
        self._max_memory_items = 100
        self._max_disk_age_seconds = 7 * 24 * 3600  # 7 days
        self._access_order: list = []
        self._cache_lock = threading.RLock()
        self._session_lock = threading.Lock()
        self._initialized = True
    
    def _get_session(self) -> requests.Session:
        """Get or create shared requests session."""
        with self._session_lock:
            if self._session is None:
                self._session = requests.Session()
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=10,
                    pool_maxsize=20,
                    max_retries=3
                )
                self._session.mount('http://', adapter)
                self._session.mount('https://', adapter)
            return self._session
    
    def _get_cache_dir(self) -> Path:
        """Get cache directory path."""
        if self._cache_dir is None:
            if hasattr(Path, 'home'):
                self._cache_dir = Path.home() / '.cache' / 'yuoop' / 'thumbnails'
            else:
                self._cache_dir = Path('/tmp/yuoop/thumbnails')
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        return self._cache_dir
    
    def _get_cache_key(self, url: str, size: tuple = (60, 60)) -> str:
        """Generate cache key from URL and size."""
        key_data = f"{url}_{size[0]}x{size[1]}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_disk_path(self, cache_key: str) -> Path:
        """Get disk cache file path."""
        return self._get_cache_dir() / f"{cache_key}.png"
    
    def get(self, url: str, size: tuple = (60, 60)) -> Optional[Image.Image]:
        """
        Get thumbnail from cache.
        
        Args:
            url: Thumbnail URL
            size: Target size (width, height)
            
        Returns:
            PIL Image copy or None if not cached
        """
        if not url:
            return None

        cache_key = self._get_cache_key(url, size)

        with self._cache_lock:
            if cache_key in self._memory_cache:
                self._touch(cache_key)
                return self._memory_cache[cache_key].copy()
        
        disk_path = self._get_disk_path(cache_key)
        if disk_path.exists():
            try:
                if time.time() - disk_path.stat().st_mtime > self._max_disk_age_seconds:
                    disk_path.unlink(missing_ok=True)
                    return None

                with Image.open(disk_path) as img:
                    cached_image = img.convert("RGB")

                self._set(cache_key, cached_image)
                return cached_image.copy()
            except Exception:
                pass
        
        return None
    
    def fetch(self, url: str, size: tuple = (60, 60), timeout: float = 5.0) -> Optional[Image.Image]:
        """
        Fetch thumbnail from URL with caching.
        
        Args:
            url: Thumbnail URL
            size: Target size (width, height)
            timeout: Request timeout in seconds
            
        Returns:
            PIL Image copy or None if fetch failed
        """
        cached = self.get(url, size)
        if cached is not None:
            return cached
        
        try:
            session = self._get_session()
            response = session.get(url, timeout=timeout, verify=True)
            response.raise_for_status()
            
            with Image.open(BytesIO(response.content)) as raw_img:
                img = raw_img.convert("RGB")
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            self._set(cache_key=self._get_cache_key(url, size), image=img, disk_image=img)
            
            return img.copy()
            
        except Exception:
            pass
        
        return None
    
    def _touch(self, cache_key: str) -> None:
        """Mark cache key as recently used."""
        if cache_key in self._access_order:
            self._access_order.remove(cache_key)
        self._access_order.append(cache_key)

    def _set(self, cache_key: str, image: Image.Image, disk_image: Optional[Image.Image] = None) -> None:
        """Store image in caches and enforce LRU eviction."""
        with self._cache_lock:
            self._touch(cache_key)
            
            while len(self._memory_cache) >= self._max_memory_items:
                oldest_key = self._access_order.pop(0)
                if oldest_key in self._memory_cache:
                    del self._memory_cache[oldest_key]
            
            self._memory_cache[cache_key] = image.copy()
        
        if disk_image is not None:
            try:
                disk_path = self._get_disk_path(cache_key)
                disk_image.save(disk_path, 'PNG')
            except Exception:
                pass
    
    def clear(self) -> None:
        """Clear all caches."""
        with self._cache_lock:
            self._memory_cache.clear()
            self._access_order.clear()
