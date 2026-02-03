import time
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, Optional, Tuple
from fastapi import HTTPException, status
from redis.asyncio import Redis
from .request import FRFRequest


class BaseThrottle(ABC):
    """
    Base throttle class

    All throttle classes should inherit from this class and implement the allow_request method.
    """

    # Whether to store throttle information in cache
    cache = defaultdict(list)
    ident_cache: Dict[str, list] = defaultdict[str, list](list)

    def __init__(self):
        self.timer = time.time

    @abstractmethod
    def allow_request(self, request: FRFRequest, view) -> bool:
        """
        Determine whether to allow the request

        Args:
            request: FRFRequest object
            view: ViewSet instance

        Returns:
            bool: True means allow request, False means reject
        """
        pass

    def get_ident(self, request: FRFRequest) -> str:
        """
        Get the unique identifier for the request

        Priority:
        1. Authenticated user -> user.id
        2. Anonymous user -> IP address

        Args:
            request: FRFRequest object

        Returns:
            str: Unique identifier
        """
        if request.user and hasattr(request.user, "id"):
            return f"user:{request.user.id}"

        # Get IP address
        if request.raw.client and request.raw.client.host:
            return f"ip:{request.raw.client.host}"

        return "anonymous"

    def get_rate(self) -> Optional[str]:
        """
        Get the throttle rate

        Format: "number/period"
        Examples:
        - "100/day"  - 100 times per day
        - "10/hour"  - 10 times per hour
        - "5/minute" - 5 times per minute
        - "1/second" - 1 time per second

        Returns:
            Optional[str]: Throttle rate string, None means no throttling
        """
        return None

    def parse_rate(self, rate: str) -> Tuple[int, int]:
        """
        Parse the throttle rate string

        Args:
            rate: Throttle rate string (e.g., "100/day")

        Returns:
            Tuple[int, int]: (number, period seconds)

        Raises:
            ValueError: If the rate format is invalid
        """
        if not rate:
            return (None, None)

        num, period = rate.split("/")
        num = int(num)

        # Period mapping
        period_map = {
            "second": 1,
            "seconds": 1,
            "minute": 60,
            "minutes": 60,
            "hour": 3600,
            "hours": 3600,
            "day": 86400,
            "days": 86400,
        }

        if period not in period_map:
            raise ValueError(
                f"Invalid period '{period}'. "
                f"Must be one of: {', '.join(period_map.keys())}"
            )

        return (num, period_map[period])

    def throttle_failure(self):
        """
        Triggered when throttle rejects the request
        Raises HTTP 429 error
        """
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Request was throttled.",
        )

    def wait(self) -> float:
        """
        Calculate the required wait time (seconds)

        Returns:
            float: Wait seconds
        """
        return 0.0


class SimpleRateThrottle(BaseThrottle):
    """
    Simple throttle base class

    Performs throttling based on the rate returned by get_rate().
    Uses ident as the throttle key.
    """

    scope: Optional[str] = None  # Throttle scope name
    THROTTLE_RATES: Dict[str, str] = {}  # Global throttle configuration

    def __init__(self):
        super().__init__()
        self.rate = self.parse_rate(self.get_rate())
        self.num_requests, self.duration = self.rate

    def get_rate(self) -> Optional[str]:
        """
        Get the throttle rate

        Priority:
        1. Check if scope is defined, get from THROTTLE_RATES
        2. Check class attribute rate
        """
        if self.scope is not None:
            return self.THROTTLE_RATES.get(self.scope)

        return super().get_rate()

    def allow_request(self, request: FRFRequest, view) -> bool:
        """
        Determine whether to allow the request

        Args:
            request: FRFRequest object
            view: ViewSet instance

        Returns:
            bool: True means allow, False means reject
        """
        if self.rate is None:
            return True

        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True

        self.ident_cache.setdefault(self.key, [])
        history = self.ident_cache[self.key]

        # Get current time
        now = self.timer()

        # Remove expired records
        while history and history[-1] <= now - self.duration:
            history.pop()

        # Check if throttle limit is exceeded
        if len(history) >= self.num_requests:
            return self.throttle_failure()

        # Record this request
        history.insert(0, now)

        return True

    def get_cache_key(self, request: FRFRequest, view) -> Optional[str]:
        """
        Get the cache key

        By default uses ident, subclasses can override this method to customize the key

        Args:
            request: FRFRequest object
            view: ViewSet instance

        Returns:
            Optional[str]: Cache key
        """
        ident = self.get_ident(request)
        return f"{self.scope or 'throttle'}:{ident}"

    def wait(self) -> float:
        """
        Calculate the required wait time

        Returns:
            float: Wait seconds
        """
        if self.key not in self.ident_cache:
            return 0.0

        history = self.ident_cache[self.key]
        if not history:
            return 0.0

        # Wait time = oldest request time + throttle period - current time
        return self.duration - (self.timer() - history[-1])


class AsyncRedisSimpleRateThrottle(SimpleRateThrottle):
    """
    Async Redis simple throttle class

    Stores throttle information based on Redis, supports distributed deployment.
    """

    scope = "anon_redis_simple"
    THROTTLE_RATES: dict = {
        "anon_redis_simple": "5/minute",
    }

    def __init__(self, redis: Redis):
        super().__init__()
        self.redis = redis

    async def allow_request(self, request: FRFRequest, view) -> bool:
        """
        Determine whether to allow the request
        """
        if self.rate is None:
            return True

        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(self.key, 0, self.timer() - self.duration)
            pipe.zcard(self.key)
            pipe.zadd(self.key, {self.timer(): self.timer()})
            pipe.expire(self.key, self.duration)
            results = await pipe.execute()

        current_count = results[1]

        if current_count >= self.num_requests:
            return self.throttle_failure()

        return True


class AnonRateThrottle(SimpleRateThrottle):
    """
    Anonymous user throttle

    Only throttles unauthenticated users.
    """

    scope = "anon"

    def get_cache_key(self, request: FRFRequest, view) -> Optional[str]:
        """
        Anonymous users use IP as key
        """
        if request.user and hasattr(request.user, "id"):
            return None

        ident = self.get_ident(request)
        return f"anon:{ident}"
