#!/usr/bin/env python3
""" expiring web cache module """

import redis
import uuid
from typing import Union, Callable, Optional
import functools

def count_calls(method: Callable) -> Callable:
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        key = method.__qualname__
        self._redis.incr(key)
        return method(self, *args, **kwargs)
    return wrapper

def call_history(method: Callable) -> Callable:
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        input_key = method.__qualname__ + ":inputs"
        output_key = method.__qualname__ + ":outputs"

        # Store input arguments
        self._redis.rpush(input_key, str(args))

        # Call the original method and store the result
        result = method(self, *args, **kwargs)
        self._redis.rpush(output_key, str(result))

        return result
    return wrapper

def replay(method: Callable) -> None:
    """Display the history of calls of a particular function."""
    redis_instance = method.__self__._redis
    method_name = method.__qualname__

    input_key = method_name + ":inputs"
    output_key = method_name + ":outputs"

    inputs = redis_instance.lrange(input_key, 0, -1)
    outputs = redis_instance.lrange(output_key, 0, -1)

    print(f"{method_name} was called {len(inputs)} times:")

    for input_data, output_data in zip(inputs, outputs):
        input_args = input_data.decode('utf-8')
        output_value = output_data.decode('utf-8')
        print(f"{method_name}(*{input_args}) -> {output_value}")

class Cache:
    def __init__(self):
        self._redis = redis.Redis()
        self._redis.flushdb()

    @count_calls
    @call_history
    def store(self, data: Union[str, bytes, int, float]) -> str:
        key = str(uuid.uuid4())
        self._redis.set(key, data)
        return key

    def get(self, key: str, fn: Optional[Callable[[bytes], Union[str, int, float]]] = None) -> Optional[Union[str, int, float]]:
        data = self._redis.get(key)
        if data is None:
            return None
        if fn is None:
            return data
        return fn(data)

    def get_str(self, key: str) -> Optional[str]:
        return self.get(key, lambda x: x.decode('utf-8'))

    def get_int(self, key: str) -> Optional[int]:
        return self.get(key, int)

    def get_call_count(self, method_name: str) -> int:
        count = self._redis.get(method_name)
        return int(count) if count else 0

    def get_input_history(self, method_name: str) -> list:
        input_key = method_name + ":inputs"
        return self._redis.lrange(input_key, 0, -1)

    def get_output_history(self, method_name: str) -> list:
        output_key = method_name + ":outputs"
        return self._redis.lrange(output_key, 0, -1)

