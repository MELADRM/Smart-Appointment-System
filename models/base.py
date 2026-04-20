"""Base class shared by every domain entity."""

from abc import ABC, abstractmethod
from datetime import datetime
from db import new_id as _new_id

class BaseModel(ABC):
    @staticmethod
    def new_id(prefix: str = 'id') -> str:
        return _new_id(prefix)

    @staticmethod
    def now_iso() -> str:
        return datetime.now().isoformat()

    @classmethod
    def from_dict(cls, data: dict):
        # Build an instance from a row dict; unknown keys are ignored.
        import inspect

        sig = inspect.signature(cls.__init__)
        allowed = {p for p in sig.parameters if p != 'self'}
        filtered = {k: v for k, v in (data or {}).items() if k in allowed}
        return cls(**filtered)

    def to_dict(self) -> dict:
        # Flatten to the dict shape save_db() expects.
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    @abstractmethod
    def validate(self) -> None:
        # Concrete classes raise ValueError with a user-facing message.
        ...

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} id={getattr(self, "id", "?")}>'
