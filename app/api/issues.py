from datetime import date
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.activity import record_activity, record_issue_changes
from app.api.members import require_project_member
from app.api.sprints import require_assignable_sprint
from app.api.watchers import ensure_watcher
from app.database import get_db
from app.models import (
    ActivityAction,
    Issue,
    IssueLink,
    IssueLinkType,
    IssuePriority,
    IssueStatus,
    IssueWatcher,
    Label,
    Project,
    Story,
)
from app.schemas import IssueBulkUpdate, IssueCreate, IssueDetail, IssueLinkRead, IssueRead, IssueUpdate

router = APIRouter(prefix="/issues", tags=["issues"])


class IssueSort(str, Enum):
    newest = "newest"
    oldest = "oldest"
    updated = "updated"
    due_date = "due_date"
    priority = "priority"


PRIORITY_RANK = case(
    {
        IssuePriority.critical.value: 0,
        IssuePriority.high.value: 1,
        IssuePriority.medium.value: 2,
        IssuePriority.low.value: 3,
    },
    value=Issue.priority,
    else_=4,
)


def _sort_order(sort: IssueSort) -> tuple:
    if sort == IssueSort.oldest:
        return (Issue.id.asc(),)
    if sort == IssueSort.updated:
        return (Issue.updated_at.desc(), Issue.id.desc())
    if sort == IssueSort.due_date:
        return (Issue.due_date.asc().nulls_last(), Issue.id.desc())
    if sort == IssueSort.priority:
        return (PRIORITY_RANK, Issue.id.desc())
    return (Issue.id.desc(),)


@router.get("", response_model=list[IssueRead])
def list_issues(
    response: Response,
    project_id: int | None = Query(default=None),
    story_id: int | None = Query(default=None),
    status_filter: IssueStatus | None = Query(default=None, alias="status"),
    priority: IssuePriority | None = Query(default=None),
    assignee_id: int | None = Query(default=None),
    label_id: int | None = Query(default=None),
    sprint_id: int | None = Query(default=None),
    blocked: bool | None = Query(default=None),
    overdue: bool | None = Query(default=None),
    due_before: date | None = Query(default=None),
    watcher_id: int | None = Query(default=None),
    unassigned: bool | None = Query(default=None),
    backlog: bool | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1),
    sort: IssueSort = Query(default=IssueSort.newest),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Issue]:
    query = db.query(Issue)
    if project_id is not None:
        query = query.filter(Issue.project_id == project_id)
    if story_id is not None:
        query = query.filter(Issue.story_id == story_id)
    if status_filter is not None:
        query = query.filter(Issue.status == status_filter.value)
    if priority is not None:
        query = query.filter(Issue.priority == priority.value)
    if assignee_id is not None:
        query = query.filter(Issue.assignee_id == assignee_id)
    if label_id is not None:
        query = query.filter(Issue.labels.any(Label.id == label_id))
    if sprint_id is not None:
        query = query.filter(Issue.sprint_id == sprint_id)
    if blocked is not None:
        open_block = (IssueLink.link_type == IssueLinkType.blocks.value) & (
            IssueLink.source.has(Issue.status != IssueStatus.closed.value)
        )
        if blocked:
            query = query.filter(Issue.inbound_links.any(open_block))
        else:
            query = query.filter(~Issue.inbound_links.any(open_block))
    if due_before is not None:
        query = query.filter(Issue.due_date.is_not(None), Issue.due_date <= due_before)
    if overdue is True:
        query = query.filter(
            Issue.due_date.is_not(None),
            Issue.due_date < date.today(),
            Issue.status != IssueStatus.closed.value,
        )
    elif overdue is False:
        query = query.filter(
            or_(
                Issue.due_date.is_(None),
                Issue.due_date >= date.today(),
                Issue.status == IssueStatus.closed.value,
            )
        )
    if watcher_id is not None:
        query = query.filter(Issue.watchers.any(IssueWatcher.user_id == watcher_id))
    if unassigned is not None:
        query = query.filter(Issue.assignee_id.is_(None) if unassigned else Issue.assignee_id.is_not(None))
    if backlog is not None:
        query = query.filter(Issue.sprint_id.is_(None) if backlog else Issue.sprint_id.is_not(None))
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                Issue.title.ilike(pattern),
                Issue.description.ilike(pattern),
                Issue.key.ilike(pattern),
            )
        )
    response.headers["X-Total-Count"] = str(query.count())
    return query.order_by(*_sort_order(sort)).offset(offset).limit(limit).all()


@router.post("", response_model=IssueRead, status_code=status.HTTP_201_CREATED)
def create_issue(payload: IssueCreate, db: Session = Depends(get_db)) -> Issue:
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if payload.story_id is not None:
        story = db.get(Story, payload.story_id)
        if not story or story.project_id != payload.project_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Story does not belong to project")

    if payload.assignee_id is not None:
        require_project_member(db, payload.project_id, payload.assignee_id)
    if payload.sprint_id is not None:
        require_assignable_sprint(db, payload.project_id, payload.sprint_id)
    if payload.actor_id is not None:
        require_project_member(db, payload.project_id, payload.actor_id)

    current = db.query(func.max(Issue.number)).filter(Issue.project_id == project.id).scalar()
    number = (current or 0) + 1
    issue = Issue(
        project_id=payload.project_id,
        number=number,
        key=f"{project.key}-{number}",
        story_id=payload.story_id,
        title=payload.title,
        description=payload.description,
        status=payload.status.value,
        priority=payload.priority.value,
        assignee_id=payload.assignee_id,
        sprint_id=payload.sprint_id,
        estimate=payload.estimate,
        due_date=payload.due_date,
    )
    db.add(issue)
    db.flush()
    record_activity(db, issue.id, ActivityAction.created, actor_id=payload.actor_id, new_value=issue.key)
    for user_id in {payload.actor_id, payload.assignee_id} - {None}:
        ensure_watcher(db, issue.id, user_id)
    db.commit()
    db.refresh(issue)
    return issue


@router.post("/bulk-update", response_model=list[IssueRead])
def bulk_update_issues(payload: IssueBulkUpdate, db: Session = Depends(get_db)) -> list[Issue]:
    issue_ids = list(dict.fromkeys(payload.issue_ids))
    issues = db.query(Issue).filter(Issue.id.in_(issue_ids)).order_by(Issue.id).all()
    if len(issues) != len(issue_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more issues were not found")
    project_ids = {issue.project_id for issue in issues}
    if len(project_ids) > 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Issues must belong to one project")
    project_id = project_ids.pop()

    data = payload.model_dump(exclude_unset=True, exclude={"issue_ids", "actor_id"})
    for required in ("status", "priority"):
        if required in data and data[required] is None:
            del data[required]
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    if payload.actor_id is not None:
        require_project_member(db, project_id, payload.actor_id)
    if data.get("status") is not None:
        data["status"] = data["status"].value
    if data.get("priority") is not None:
        data["priority"] = data["priority"].value
    if data.get("assignee_id") is not None:
        require_project_member(db, project_id, data["assignee_id"])
    if data.get("sprint_id") is not None:
        require_assignable_sprint(db, project_id, data["sprint_id"])

    for issue in issues:
        record_issue_changes(db, issue, data, payload.actor_id)
        for key, value in data.items():
            setattr(issue, key, value)
    if data.get("assignee_id") is not None:
        for issue in issues:
            ensure_watcher(db, issue.id, data["assignee_id"])

    db.commit()
    for issue in issues:
        db.refresh(issue)
    return issues


@router.get("/{issue_id}", response_model=IssueDetail)
def get_issue(issue_id: int, db: Session = Depends(get_db)) -> IssueDetail:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    links = (
        db.query(IssueLink)
        .filter(or_(IssueLink.source_id == issue_id, IssueLink.target_id == issue_id))
        .order_by(IssueLink.id)
        .all()
    )
    detail = IssueDetail.model_validate(issue)
    detail.links = [IssueLinkRead.model_validate(link) for link in links]
    return detail


@router.patch("/{issue_id}", response_model=IssueRead)
def update_issue(issue_id: int, payload: IssueUpdate, db: Session = Depends(get_db)) -> Issue:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    data = payload.model_dump(exclude_unset=True)
    actor_id = data.pop("actor_id", None)
    for required in ("title", "status", "priority"):
        if required in data and data[required] is None:
            del data[required]
    if actor_id is not None:
        require_project_member(db, issue.project_id, actor_id)

    if "story_id" in data and data["story_id"] is not None:
        story = db.get(Story, data["story_id"])
        if not story or story.project_id != issue.project_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Story does not belong to project")

    if "status" in data and data["status"] is not None:
        data["status"] = data["status"].value
    if "priority" in data and data["priority"] is not None:
        data["priority"] = data["priority"].value
    if data.get("assignee_id") is not None:
        require_project_member(db, issue.project_id, data["assignee_id"])
    if data.get("sprint_id") is not None:
        require_assignable_sprint(db, issue.project_id, data["sprint_id"])

    record_issue_changes(db, issue, data, actor_id)
    for key, value in data.items():
        setattr(issue, key, value)
    if data.get("assignee_id") is not None:
        ensure_watcher(db, issue.id, data["assignee_id"])

    db.commit()
    db.refresh(issue)
    return issue


@router.delete("/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_issue(issue_id: int, db: Session = Depends(get_db)) -> None:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    db.delete(issue)
    db.commit()
