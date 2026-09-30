from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.members import require_project_member
from app.api.sprints import require_assignable_sprint
from app.database import get_db
from app.models import Issue, IssuePriority, IssueStatus, Label, Project, Story
from app.schemas import IssueCreate, IssueRead, IssueUpdate

router = APIRouter(prefix="/issues", tags=["issues"])


@router.get("", response_model=list[IssueRead])
def list_issues(
    project_id: int | None = Query(default=None),
    story_id: int | None = Query(default=None),
    status_filter: IssueStatus | None = Query(default=None, alias="status"),
    priority: IssuePriority | None = Query(default=None),
    assignee_id: int | None = Query(default=None),
    label_id: int | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1),
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
    if q:
        query = query.filter(Issue.title.ilike(f"%{q}%"))
    return query.order_by(Issue.id.desc()).all()


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
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


@router.get("/{issue_id}", response_model=IssueRead)
def get_issue(issue_id: int, db: Session = Depends(get_db)) -> Issue:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return issue


@router.patch("/{issue_id}", response_model=IssueRead)
def update_issue(issue_id: int, payload: IssueUpdate, db: Session = Depends(get_db)) -> Issue:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    data = payload.model_dump(exclude_unset=True)

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

    for key, value in data.items():
        setattr(issue, key, value)

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
