from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountCheckerBatchIn(BaseModel):
    user_id: int
    total_tasks: int
    completed_tasks: int = 0
    status: str = "processing"


class AccountCheckerBatchOut(BaseModel):
    id: int
    user_id: int
    total_tasks: int
    completed_tasks: int
    status: str
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AccountCheckerBatchStatusOut(BaseModel):
    batch_id: int
    user_id: int
    status: str
    total_tasks: int
    completed_tasks: int
    created_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = Field(
        default=None,
        description="Секунды от принятия пачки до завершения (все фоновые задачи); только когда status=completed",
    )
    elapsed_seconds: float = Field(
        description="Секунды с момента принятия пачки: до now если ещё идёт, или до completed_at",
    )
