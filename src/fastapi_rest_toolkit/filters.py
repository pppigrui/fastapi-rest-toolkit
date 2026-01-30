from typing import Any, Dict, Sequence, Tuple

from .contextvar import ordering_parsed


class CRUDPlusFilterBackend:
    reserved = {"limit", "offset", "search", "ordering"}

    def apply(self, *, request, view, filters: Dict[str, Any]) -> Dict[str, Any]:
        qp = dict(request.query_params or {})
        for k in list(qp.keys()):
            if k in self.reserved:
                qp.pop(k, None)
        filters.update(qp)
        return filters


class SearchFilterBackend:
    param_name = "search"

    def apply(self, *, request, view, filters: Dict[str, Any]) -> Dict[str, Any]:
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

    def parse_ordering(self, ordering_fields: Sequence[str]) -> Tuple[list, list]:
        cols = []
        orders = []
        for field in ordering_fields:
            desc = field.startswith("-")
            name = field[1:] if desc else field
            cols.append(name)
            orders.append("desc" if desc else "asc")
        if len(cols) != len(orders):
            return [], []
        if not cols:
            return [], []
        return cols, orders

    def apply(self, *, request, view, filters: Dict[str, Any]) -> Dict[str, Any]:
        ordering = bool(
            (request.query_params or {}).get(self.param_name, True)
        )  # default to True
        if not ordering:
            return filters
        ordering_fields: Sequence[str] = getattr(view, "ordering_fields", ())
        if not ordering_fields:
            return filters
        parsed = self.parse_ordering(ordering_fields)
        ordering_parsed.set(parsed)
        return filters
