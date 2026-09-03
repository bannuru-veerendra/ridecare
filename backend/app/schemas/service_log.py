import uuid
from datetime import date as dt_date

from pydantic import BaseModel, ConfigDict, model_validator

from app.utils.dates import app_today


class ServiceLogCreate(BaseModel):
    """Request body for POST /service_logs"""
    date: dt_date
    odometer: int
    service_center: str | None = None
    total_cost: float
    services_done: list[str]
    next_service_date: dt_date | None = None
    next_service_odometer: int | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_values(self):
        if self.date > app_today():
            raise ValueError("Service log date cannot be in the future")
        if self.total_cost <= 0:
            raise ValueError("Total cost must be greater than 0")
        if self.odometer <= 0:
            raise ValueError("Odometer must be greater than 0")
        if not self.services_done:
            raise ValueError("At least one service must be done")
        if self.next_service_odometer is not None and self.next_service_odometer <= self.odometer:
            raise ValueError("Next service odometer must be greater than the current odometer")
        return self


class ServiceLogUpdate(BaseModel):
    """Request body for PATCH /service_logs/{service_log_id}"""
    date: dt_date | None = None
    odometer: int | None = None
    service_center: str | None = None
    total_cost: float | None = None
    services_done: list[str] | None = None
    next_service_date: dt_date | None = None
    next_service_odometer: int | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_values(self):
        if self.date is not None and self.date > app_today():
            raise ValueError("Service log date cannot be in the future")
        if self.total_cost is not None and self.total_cost <= 0:
            raise ValueError("Total cost must be greater than 0")
        if self.odometer is not None and self.odometer <= 0:
            raise ValueError("Odometer must be greater than 0")
        if self.services_done is not None and not self.services_done:
            raise ValueError("At least one service must be done")
        if (
            self.next_service_odometer is not None
            and self.odometer is not None
            and self.next_service_odometer <= self.odometer
        ):
            raise ValueError("Next service odometer must be greater than the current odometer")
        return self


class ServiceLogResponse(BaseModel):
    """Response body for service log endpoints"""
    id: uuid.UUID
    vehicle_id: uuid.UUID
    date: dt_date
    odometer: int
    service_center: str | None = None
    total_cost: float
    services_done: list[str]
    next_service_date: dt_date | None = None
    next_service_odometer: int | None = None
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SuggestNextDueRequest(BaseModel):
    """Body for POST /service_logs/suggest-next-due"""
    date: dt_date
    odometer: int
    services_done: list[str]

    @model_validator(mode="after")
    def validate_values(self):
        if self.odometer <= 0:
            raise ValueError("Odometer must be greater than 0")
        if not self.services_done:
            raise ValueError("At least one service must be done")
        return self


class SuggestNextDueResponse(BaseModel):
    next_service_date: dt_date | None = None
    next_service_odometer: int | None = None
    matched_tasks: list[str] = []

