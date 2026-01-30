from typing import Any, Dict, List, Optional, Sequence, Tuple, TypeVar, Generic

ModelT = TypeVar("ModelT")


class CRUDService(Generic[ModelT]):
    def __init__(self, crud, model):
        self.crud = crud
        self.model = model

    async def list(
        self,
        session,
        *,
        filters: Dict[str, Any],
        limit: int,
        offset: int,
        ordering: Optional[Tuple[str, str]] = None,
        load_strategies: Optional[Sequence[str]] = None,
        join_conditions: Optional[Any] = None,
    ) -> tuple[int, List[ModelT]]:
        total = await self.crud.count(session, **filters)

        if ordering:
            sort_columns, sort_orders = ordering
            items = await self.crud.select_models_order(
                session,
                sort_columns=sort_columns,
                sort_orders=sort_orders,
                limit=limit,
                offset=offset,
                load_strategies=load_strategies,
                join_conditions=join_conditions,
                **filters,
            )
        else:
            items = await self.crud.select_models(
                session,
                limit=limit,
                offset=offset,
                load_strategies=load_strategies,
                join_conditions=join_conditions,
                **filters,
            )
        return total, list(items)

    async def retrieve(
        self, session, *, pk: Any, load_strategies=None, join_conditions=None
    ):
        return await self.crud.select_model(
            session,
            pk=pk,
            load_strategies=load_strategies,
            join_conditions=join_conditions,
        )

    async def create(self, session, *, obj_in: Any):
        return await self.crud.create_model(session, obj_in, flush=True)

    async def update(self, session, *, pk: Any, obj_in: Any):
        return await self.crud.update_model(session, pk=pk, obj=obj_in, flush=True)

    async def destroy(self, session, *, pk: Any):
        return await self.crud.delete_model(session, pk=pk, flush=True)
