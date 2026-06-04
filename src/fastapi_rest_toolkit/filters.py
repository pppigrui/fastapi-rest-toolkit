from typing import Any, Dict, Sequence, Tuple, TYPE_CHECKING

from fastapi import HTTPException, status


if TYPE_CHECKING:
    from .viewset import ViewSet
    from .request import FRFRequest


class CRUDPlusFilterBackend:
    reserved = {"limit", "offset", "search", "ordering"}

    def apply(
        self, *, request: "FRFRequest", view: "ViewSet", filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        qp = dict(request.query_params or {})
        for k in list(qp.keys()):
            if k in self.reserved:
                qp.pop(k, None)
        filters.update(qp)
        return filters


class SearchFilterBackend:
    param_name = "search"

    def apply(
        self, *, request: "FRFRequest", view: "ViewSet", filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        term = (request.query_params or {}).get(self.param_name)
        if not term:
            return filters
        search_fields: Sequence[str] = getattr(view, "search_fields", ())
        if not search_fields:
            return filters

        # crud-plus supports __or__ mapping
        or_map = {f"{f}__like": f"%{term}%" for f in search_fields}
        if isinstance(filters.get("__or__"), dict):
            filters["__or__"].update(or_map)
        else:
            filters["__or__"] = or_map
        return filters


class OrderingFilterBackend:
    param_name = "ordering"

    def parse_ordering(
        self, ordering: str, allowed_fields: Sequence[str]
    ) -> Tuple[list[str], list[str]]:
        allowed = {field.lstrip("-") for field in allowed_fields}
        cols = []
        orders = []
        for field in ordering.split(","):
            field = field.strip()
            if not field:
                continue
            desc = field.startswith("-")
            name = field[1:] if desc else field
            if allowed and name not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid ordering field: {name}",
                )
            cols.append(name)
            orders.append("desc" if desc else "asc")
        return cols, orders

    def apply(
        self, *, request: "FRFRequest", view: "ViewSet", filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        request.ordering = None
        ordering = (request.query_params or {}).get(self.param_name)
        if not ordering:
            return filters
        ordering_fields: Sequence[str] = getattr(view, "ordering_fields", ())
        if not ordering_fields:
            return filters
        parsed = self.parse_ordering(ordering, ordering_fields)
        request.ordering = parsed if parsed[0] else None
        return filters
