from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class PermitCreate(BaseModel):
    zone_id: uuid.UUID
    permit_type: Literal["hot_work", "confined_space", "excavation", "electrical"]
    issued_to_worker_id: uuid.UUID | None = None
    valid_from: datetime
    valid_to: datetime
    notes: str | None = None


class PermitResponse(BaseModel):
    id: uuid.UUID
    zone_id: uuid.UUID
    permit_type: str
    issued_to_worker_id: uuid.UUID | None = None
    issued_by_user_id: uuid.UUID | None = None
    valid_from: datetime
    valid_to: datetime
    status: str
    notes: str | None = None

    class Config:
        from_attributes = True
