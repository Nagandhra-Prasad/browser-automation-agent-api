from typing import Literal

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    role: Literal["user", "admin"]
    my_tasks: int
    total_users: int | None = None
    total_tasks: int | None = None
