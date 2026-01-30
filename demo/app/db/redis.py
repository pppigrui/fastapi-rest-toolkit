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
    Redis 客户端包装类
    - 支持根据不同 redis_url 创建多个实例
    - 每个实例内部维护自己的连接池和 Redis 客户端
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or os.environ.get("REDIS_URI", "redis://localhost:6379/0")
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
                socket_timeout=5,  # 建议缩短到5s，快速失败比慢速等待好
                socket_connect_timeout=5,
                # TCP Keepalive 深度优化：防止防火墙切断空闲连接
                socket_keepalive=True,
                socket_keepalive_options={
                    socket.TCP_KEEPALIVE: 60,  # 60秒空闲后开始发包
                    socket.TCP_KEEPCNT: 3,  # 连续探测3次失败则断开
                    socket.TCP_KEEPINTVL: 10,  # 探测间隔10秒
                },
                # 健康检查与重试
                health_check_interval=25,  # 略小于服务器 timeout 或 TCP Keepidle
                retry=retry,  # 注入重试实例
                retry_on_timeout=True,
                retry_on_error=[ConnectionError, TimeoutError],  # 指定错误类型重试
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
                retry_on_error=[RedisConnectionError],  # 连接错误时重试
            )
        return self._client

    async def close(self) -> None:
        """关闭当前实例的 Redis 连接池和客户端"""
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
        检查当前实例的 Redis 连接健康状态

        Returns:
            bool: True 表示连接健康，False 表示连接异常
        """
        try:
            client = self.get_client()
            await client.ping()
            return True
        except Exception:
            return False

    async def reconnect(self) -> None:
        """
        重新连接当前实例的 Redis

        Raises:
            RedisError: 当重连失败时抛出异常
        """

        # 先关闭现有连接
        await self.close()

        # 重新创建连接
        self._create_connection_pool()
        # type: ignore[arg-type]
        self._client = Redis(connection_pool=self._pool)

        # 验证连接
        if not await self.check_health():
            raise RedisError("Failed to reconnect to Redis...", exc_info=True)


# ------- 默认实例（保持兼容，也方便直接用一个默认 Redis） --------
default_redis = RedisClient()  # 默认使用 app_config.redis_config.cache_url
redis_client = default_redis.get_client()


def get_redis_client():
    return RedisClient().get_client()


__all__ = ["redis_client"]
