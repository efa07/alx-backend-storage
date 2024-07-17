#!/usr/bin/env python3
""" expiring web cache module """


import redis
import requests
from typing import Callable
import functools


_redis = redis.Redis()


def count_calls(method: Callable) -> Callable:
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        url = args[0]
        count_key = f"count:{url}"
        _redis.incr(count_key)
        return method(*args, **kwargs)
    return wrapper


def cache_with_expiration(expiration: int):
    def decorator(method: Callable) -> Callable:
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            url = args[0]
            cache_key = f"cache:{url}"
            cached_content = _redis.get(cache_key)
            if cached_content:
                return cached_content.decode('utf-8')
            content = method(*args, **kwargs)
            _redis.setex(cache_key, expiration, content)
            return content
        return wrapper
    return decorator


@count_calls
@cache_with_expiration(10)
def get_page(url: str) -> str:
    response = requests.get(url)
    return response.text
