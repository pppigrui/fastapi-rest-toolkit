import os
import socket

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError


class RedisClient:
    """
    Redis client wrapper class
    - Supports creating multiple instances based on different redis_url
    - Each instance maintains its own connection pool and Redis client internally
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or os.environ.get(
            "REDIS_URI", "redis://localhost:6379/0"
        )
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

    # ----------------- 内部方法 -----------------
    def _create_connection_pool(self) -> ConnectionPool:
        """创建 Redis 连接池（按实例）"""
        if self._pool is not None:
            return self._pool

        try:
            retry = Retry(ExponentialBackoff(cap=5, base=1), 3)

            self._pool = redis.ConnectionPool.from_url(
                self._redis_url,
                decode_responses=True,
                # 超时配置
                socket_timeout=5,  # Recommended to reduce to 5s, fast failure is better than slow waiting
                socket_connect_timeout=5,
                # TCP Keepalive deep optimization: prevent firewall from cutting idle connections
                socket_keepalive=True,
                socket_keepalive_options={
                    socket.TCP_KEEPCNT: 3,  # Disconnect after 3 consecutive failed probes
                    socket.TCP_KEEPINTVL: 10,  # Probe interval 10 seconds
                },
                # Health check and retry
                health_check_interval=25,  # Slightly less than server timeout or TCP Keepidle
                retry=retry,  # Inject retry instance
                retry_on_timeout=True,
                retry_on_error=[
                    ConnectionError,
                    TimeoutError,
                ],  # Retry on specified error types
                max_connections=50,
            )
            return self._pool

        except Exception:
            raise

    # ----------------- 对外方法 -----------------
    def get_client(self) -> Redis:
        """
        获取 Redis 客户端实例（按实例懒加载）

        Returns:
            Redis: Redis 客户端实例
        """
        if self._client is None or self._pool is None:
            pool = self._create_connection_pool()
            self._client = Redis(
                connection_pool=pool,
                retry_on_timeout=True,
                retry_on_error=[RedisConnectionError],  # Retry on connection errors
            )
        return self._client

    async def close(self) -> None:
        """Close the current instance's Redis connection pool and client"""
        try:
            if self._client is not None:
                await self._client.aclose()
                self._client = None

            if self._pool is not None:
                await self._pool.aclose()
                self._pool = None
        except Exception:
            raise

    async def check_health(self) -> bool:
        """
        Check the health status of the current instance's Redis connection

        Returns:
            bool: True means connection is healthy, False means connection is abnormal
        """
        try:
            client = self.get_client()
            await client.ping()
            return True
        except Exception:
            return False

    async def reconnect(self) -> None:
        """
        Reconnect the current instance's Redis

        Raises:
            RedisError: Raises exception when reconnection fails
        """

        # Close existing connection first
        await self.close()

        # Recreate connection
        self._create_connection_pool()
        # type: ignore[arg-type]
        self._client = Redis(connection_pool=self._pool)

        # Verify connection
        if not await self.check_health():
            raise RedisError("Failed to reconnect to Redis...", exc_info=True)


# ------- Default instance (maintain compatibility, also convenient to use a default Redis directly) --------
default_redis = RedisClient()  # Defaults to app_config.redis_config.cache_url
redis_client = default_redis.get_client()


def get_redis_client():
    return RedisClient().get_client()


__all__ = ["redis_client"]
