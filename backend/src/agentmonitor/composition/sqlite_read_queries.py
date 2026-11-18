"""Bound read-only connection reuse to a synchronous application-port call."""

from collections.abc import Callable

from agentmonitor.adapters.persistence._shared.sqlite.core.policy import (
    DatabaseRefV1,
    sqlite_read_query_scope,
)


def scoped_sqlite_read[**P, T](
    reference: DatabaseRefV1, query: Callable[P, T]
) -> Callable[P, T]:
    def read(*args: P.args, **kwargs: P.kwargs) -> T:
        with sqlite_read_query_scope(reference):
            return query(*args, **kwargs)

    return read
