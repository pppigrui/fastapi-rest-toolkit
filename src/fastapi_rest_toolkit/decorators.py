from functools import wraps
from typing import Sequence, Optional


def action(
    *,
    methods: Sequence[str] = ("get",),
    detail: bool = True,
    url_path: Optional[str] = None,
):
    """
    Decorator to mark a ViewSet method as a custom action, similar to DRF's @action

    Args:
        methods: List of allowed HTTP methods, defaults to ("get",)
        detail: Whether it's a detail action, True means pk is required, False means list-level action
        url_path: Custom URL path, defaults to the method name

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
        # Store action metadata on the function object
        func.is_action = True
        func.action_methods = tuple(methods)
        func.action_detail = detail
        func.action_url_path = url_path if url_path else func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Preserve action metadata on wrapper
        wrapper.is_action = True
        wrapper.action_methods = func.action_methods
        wrapper.action_detail = func.action_detail
        wrapper.action_url_path = func.action_url_path

        return wrapper

    return decorator
