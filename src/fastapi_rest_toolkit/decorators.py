from functools import wraps
from typing import Sequence, Optional


def action(
    *,
    methods: Sequence[str] = ("get",),
    detail: bool = True,
    url_path: Optional[str] = None,
):
    """
    标记 ViewSet 方法为自定义 action 的装饰器，类似于 DRF 的 @action

    Args:
        methods: 允许的 HTTP 方法列表，默认为 ("get",)
        detail: 是否为 detail action，True 表示需要 pk，False 表示 list-level action
        url_path: 自定义 URL 路径，默认使用方法名

    Usage:
        class MyViewSet(ViewSet):
            @action(methods=["post"], detail=True)
            async def custom_action(self, request, session, pk):
                # detail=True: /prefix/{pk}/custom_action/
                pass

            @action(methods=["get"], detail=False, url_path="special")
            async def list_action(self, request, session):
                # detail=False: /prefix/special/
                pass
    """
    def decorator(func):
        # 将 action 元数据存储到函数对象上
        func.is_action = True
        func.action_methods = tuple(methods)
        func.action_detail = detail
        func.action_url_path = url_path if url_path else func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # 保留 action 元数据到 wrapper
        wrapper.is_action = True
        wrapper.action_methods = func.action_methods
        wrapper.action_detail = func.action_detail
        wrapper.action_url_path = func.action_url_path

        return wrapper

    return decorator
