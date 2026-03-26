import contextvars

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    'correlation_id', default='no-correlation-id'
)

def set_correlation_id(cid: str):
    _correlation_id.set(cid)

def get_correlation_id() -> str:
    return _correlation_id.get()
