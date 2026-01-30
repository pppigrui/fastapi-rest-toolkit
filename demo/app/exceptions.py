from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


async def integrity_error_handler(
    request: Request,
    exc: IntegrityError
) -> JSONResponse:
    """
    处理数据库完整性约束错误（如唯一约束冲突）
    """
    # 解析错误信息
    error_message = str(exc.orig)

    # 提取字段名和值
    detail = "数据冲突"

    if "UNIQUE constraint failed" in error_message:
        # 解析类似 "UNIQUE constraint failed: users.email" 的错误
        parts = error_message.split(":")
        if len(parts) > 1:
            constraint_info = parts[1].strip()
            # 获取字段名（表名.字段名 -> 字段名）
            field = constraint_info.split(".")[-1] if "." in constraint_info else constraint_info
            detail = f"{field} 已存在"
    else:
        detail = error_message

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": detail,
            "error_type": "integrity_error"
        }
    )


async def generic_database_error_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    处理其他数据库错误
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "数据库操作失败",
            "error_type": "database_error"
        }
    )


def register_exception_handlers(app):
    """
    注册所有异常处理器
    """
    app.add_exception_handler(IntegrityError, integrity_error_handler)
