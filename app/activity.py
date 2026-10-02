from sqlalchemy.orm import Session

from app.models import Activity, ActivityAction, Issue

TRACKED_FIELDS = ("title", "description", "status", "priority", "assignee_id", "sprint_id", "story_id")


def _text(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def record_activity(
    db: Session,
    issue_id: int,
    action: ActivityAction,
    actor_id: int | None = None,
    field: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
) -> None:
    db.add(
        Activity(
            issue_id=issue_id,
            actor_id=actor_id,
            action=action.value,
            field=field,
            old_value=old_value,
            new_value=new_value,
        )
    )


def record_issue_changes(db: Session, issue: Issue, changes: dict, actor_id: int | None) -> None:
    for field in TRACKED_FIELDS:
        if field not in changes:
            continue
        old_value = getattr(issue, field)
        new_value = changes[field]
        if old_value == new_value:
            continue
        record_activity(
            db,
            issue.id,
            ActivityAction.updated,
            actor_id=actor_id,
            field=field,
            old_value=_text(old_value),
            new_value=_text(new_value),
        )
