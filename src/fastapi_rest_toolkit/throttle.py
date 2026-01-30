import time
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, Optional, Tuple
from fastapi import HTTPException, status
from redis.asyncio import Redis
from .request import FRFRequest


class BaseThrottle(ABC):
    """
    基础限流类

    所有限流类都应该继承此类并实现 allow_request 方法。
    """

    # 是否在缓存中存储限流信息
    cache = defaultdict(list)
    ident_cache: Dict[str, list] = defaultdict[str, list](list)

    def __init__(self):
        self.timer = time.time

    @abstractmethod
    def allow_request(self, request: FRFRequest, view) -> bool:
        """
        判断是否允许请求

        Args:
            request: FRFRequest 对象
            view: ViewSet 实例

        Returns:
            bool: True 表示允许请求，False 表示拒绝
        """
        pass

    def get_ident(self, request: FRFRequest) -> str:
        """
        获取请求的唯一标识符

        优先级：
        1. 认证用户 -> user.id
        2. 匿名用户 -> IP 地址

        Args:
            request: FRFRequest 对象

        Returns:
            str: 唯一标识符
        """
        if request.user and hasattr(request.user, "id"):
            return f"user:{request.user.id}"

        # 获取 IP 地址
        if request.raw.client and request.raw.client.host:
            return f"ip:{request.raw.client.host}"

        return "anonymous"

    def get_rate(self) -> Optional[str]:
        """
        获取限流速率

        格式: "数量/周期"
        例如:
        - "100/day"  - 每天 100 次
        - "10/hour"  - 每小时 10 次
        - "5/minute" - 每分钟 5 次
        - "1/second" - 每秒 1 次

        Returns:
            Optional[str]: 限流速率字符串，None 表示不限流
        """
        return None

    def parse_rate(self, rate: str) -> Tuple[int, int]:
        """
        解析限流速率字符串

        Args:
            rate: 限流速率字符串 (如 "100/day")

        Returns:
            Tuple[int, int]: (数量, 周期秒数)

        Raises:
            ValueError: 如果速率格式无效
        """
        if not rate:
            return (None, None)

        num, period = rate.split("/")
        num = int(num)

        # 周期映射
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
        限流拒绝时触发
        抛出 HTTP 429 错误
        """
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Request was throttled.",
        )

    def wait(self) -> float:
        """
        计算需要等待的时间（秒）

        Returns:
            float: 等待秒数
        """
        return 0.0


class SimpleRateThrottle(BaseThrottle):
    """
    简单限流基类

    基于 get_rate() 返回的速率进行限流。
    使用 ident 作为限流 key。
    """

    scope: Optional[str] = None  # 限流作用域名称
    THROTTLE_RATES: Dict[str, str] = {}  # 全局限流配置

    def __init__(self):
        super().__init__()
        self.rate = self.parse_rate(self.get_rate())
        self.num_requests, self.duration = self.rate

    def get_rate(self) -> Optional[str]:
        """
        获取限流速率

        优先级：
        1. 查看是否有 scope 定义，从 THROTTLE_RATES 获取
        2. 查看类属性 rate
        """
        if self.scope is not None:
            return self.THROTTLE_RATES.get(self.scope)

        return super().get_rate()

    def allow_request(self, request: FRFRequest, view) -> bool:
        """
        判断是否允许请求

        Args:
            request: FRFRequest 对象
            view: ViewSet 实例

        Returns:
            bool: True 表示允许，False 表示拒绝
        """
        if self.rate is None:
            return True

        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True

        self.ident_cache.setdefault(self.key, [])
        history = self.ident_cache[self.key]

        # 获取当前时间
        now = self.timer()

        # 移除过期记录
        while history and history[-1] <= now - self.duration:
            history.pop()

        # 检查是否超过限流
        if len(history) >= self.num_requests:
            return self.throttle_failure()

        # 记录本次请求
        history.insert(0, now)

        return True

    def get_cache_key(self, request: FRFRequest, view) -> Optional[str]:
        """
        获取缓存 key

        默认使用 ident，子类可以重写此方法来自定义 key

        Args:
            request: FRFRequest 对象
            view: ViewSet 实例

        Returns:
            Optional[str]: 缓存 key
        """
        ident = self.get_ident(request)
        return f"{self.scope or 'throttle'}:{ident}"

    def wait(self) -> float:
        """
        计算需要等待的时间

        Returns:
            float: 等待秒数
        """
        if self.key not in self.ident_cache:
            return 0.0

        history = self.ident_cache[self.key]
        if not history:
            return 0.0

        # 等待时间 = 最旧的请求时间 + 限流周期 - 当前时间
        return self.duration - (self.timer() - history[-1])


class AsyncRedisSimpleRateThrottle(SimpleRateThrottle):
    """
    异步 Redis 简单限流类

    基于 Redis 存储限流信息，支持分布式部署。
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
        判断是否允许请求
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
    匿名用户限流

    仅对未认证用户进行限流。
    """

    scope = "anon"

    def get_cache_key(self, request: FRFRequest, view) -> Optional[str]:
        """
        匿名用户使用 IP 作为 key
        """
        if request.user and hasattr(request.user, "id"):
            return None

        ident = self.get_ident(request)
        return f"anon:{ident}"
