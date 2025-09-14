from dataclasses import dataclass
from typing import Optional

@dataclass
class SimpleOp:
    """
    Small helper representing either an insert or delete operation.
    type: 'insert' or 'delete'
    pos: integer position (0..len)
    text: str (for insert) or None
    length: int (for delete) or None
    user_id: str (for tie-breaker)
    """
    type: str
    pos: int
    text: str | None = None
    length: int | None = None
    user_id: str | None = None
