import hashlib
import json
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class Status(StrEnum):
    pending = "pendiente"
    processing = "en_proceso"
    shipped = "enviado"
    delivered = "entregado"


NEXT_STATUS = {
    Status.pending: Status.processing,
    Status.processing: Status.shipped,
    Status.shipped: Status.delivered,
}


class OrderFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100, pattern=r"^[^\x00-\x1f\x7f]+$")]
    item: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160, pattern=r"^[^\x00-\x1f\x7f]+$")]
    quantity: Annotated[int, Field(strict=True, ge=1, le=999)]


class OrderUpdate(OrderFields):
    status: Status
    version: Annotated[int, Field(strict=True, ge=1, lt=2147483647)]


class OrderDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Annotated[int, Field(strict=True, ge=1, lt=2147483647)]


def can_transition(current: Status, requested: Status) -> bool:
    return requested == current or NEXT_STATUS.get(current) == requested


def fingerprint(method: str, path: str, data: BaseModel) -> str:
    encoded = json.dumps([method, path, data.model_dump(mode="json")], sort_keys=True)
    return hashlib.sha256(encoded.encode()).hexdigest()
