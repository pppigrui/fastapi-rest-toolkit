from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


async def integrity_error_handler(
    request: Request, exc: IntegrityError
) -> JSONResponse:
    """
    Handle database integrity constraint errors (such as unique constraint conflicts)
    """
    # Parse error message
    error_message = str(exc.orig)

    # Extract field name and value
    detail = "Data conflict"

    if "UNIQUE constraint failed" in error_message:
        # Parse errors like "UNIQUE constraint failed: users.email"
        parts = error_message.split(":")
        if len(parts) > 1:
            constraint_info = parts[1].strip()
            # Get field name (table_name.field_name -> field_name)
            field = (
                constraint_info.split(".")[-1]
                if "." in constraint_info
                else constraint_info
            )
            detail = f"{field} already exists"
    else:
        detail = error_message

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": detail, "error_type": "integrity_error"},
    )


async def generic_database_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handle other database errors
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database operation failed", "error_type": "database_error"},
    )


def register_exception_handlers(app):
    """
    Register all exception handlers
    """
    app.add_exception_handler(IntegrityError, integrity_error_handler)
