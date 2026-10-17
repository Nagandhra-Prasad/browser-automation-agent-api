from app.repositories.result_repository import ResultRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.job import JobListing
from app.schemas.result_feed import ResultTableRow


class ResultFeedService:
    async def table_for_user(self, user_id: str, admin: bool = False) -> list[ResultTableRow]:
        if admin:
            rows = await ResultRepository().list_all()
        else:
            rows = await ResultRepository().list_by_user_id(user_id)
            if not rows:
                tasks = await TaskRepository().list_by_user(user_id, limit=300)
                task_ids = [t["id"] for t in tasks]
                rows = await ResultRepository().list_by_user_tasks(task_ids)

        return await self._enrich(rows)

    async def _enrich(self, rows: list[dict]) -> list[ResultTableRow]:
        task_repo = TaskRepository()
        user_repo = UserRepository()
        out: list[ResultTableRow] = []

        for row in rows:
            task = await task_repo.get_by_id(row["task_id"])
            user_id = row.get("user_id") or (task["user_id"] if task else None)
            user_name = None
            user_email = None
            if user_id:
                user = await user_repo.get_by_id(user_id)
                if user:
                    user_name = user["name"]
                    user_email = user["email"]

            data = row.get("data") or {}
            job_rows = data.get("jobs") or []
            jobs = [JobListing.model_validate(j) for j in job_rows]

            out.append(
                ResultTableRow(
                    id=row["id"],
                    task_id=row["task_id"],
                    session_id=row["session_id"],
                    conversation_id=row.get("conversation_id"),
                    user_id=user_id,
                    user_name=user_name,
                    user_email=user_email,
                    task_name=task["task_name"] if task else None,
                    command=task["command"] if task else data.get("command"),
                    website=task["website"] if task else None,
                    summary=row.get("summary"),
                    job_count=len(jobs),
                    jobs=jobs,
                    timestamp=row["timestamp"],
                )
            )
        return out
