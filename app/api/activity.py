from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Activity, ActivityAction, Issue, Project
from app.schemas import ActivityRead

router = APIRouter(tags=["activity"])


@router.get("/issues/{issue_id}/activity", response_model=list[ActivityRead])
def list_activity(
    issue_id: int,
    field: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
) -> list[Activity]:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    query = db.query(Activity).filter(Activity.issue_id == issue_id)
    if field is not None:
        query = query.filter(Activity.field == field)
    return query.order_by(Activity.id).all()


@router.get("/projects/{project_id}/activity", response_model=list[ActivityRead])
def project_activity(
    project_id: int,
    actor_id: int | None = Query(default=None),
    action: ActivityAction | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Activity]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    query = db.query(Activity).join(Issue, Activity.issue_id == Issue.id).filter(Issue.project_id == project_id)
    if actor_id is not None:
        query = query.filter(Activity.actor_id == actor_id)
    if action is not None:
        query = query.filter(Activity.action == action.value)
    if since is not None:
        query = query.filter(Activity.created_at >= since)
    if until is not None:
        query = query.filter(Activity.created_at < until)
    return query.order_by(Activity.id.desc()).offset(offset).limit(limit).all()
