import typing as t

T = t.TypeVar("T")

def unwrap(value: T | None, msg: str = "expected value, got None") -> T:
    assert value is not None, msg
    return value

def clip(value: str, size: int) -> str:
    assert size > 3, "size must be at least 3"
    if len(value) > size:
        return value[0:size-3] + "..."
    return value
