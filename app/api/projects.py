from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Issue, IssueLink, IssueLinkType, IssuePriority, IssueStatus, Project, Sprint, SprintStatus
from app.schemas import AssigneeWorkload, ProjectCreate, ProjectRead, ProjectSummary, ProjectUpdate, SprintRead

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(
    q: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
) -> list[Project]:
    query = db.query(Project)
    if q:
        pattern = f"%{q}%"
        query = query.filter(or_(Project.name.ilike(pattern), Project.key.ilike(pattern)))
    return query.order_by(Project.id.desc()).all()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    existing = db.query(Project).filter(Project.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project name already exists")

    key = payload.key.upper()
    if db.query(Project).filter(Project.key == key).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project key already exists")

    project = Project(key=key, name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("/{project_id}/summary", response_model=ProjectSummary)
def project_summary(project_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    issues = db.query(Issue).filter(Issue.project_id == project_id)

    by_status = {item.value: 0 for item in IssueStatus}
    for value, count in issues.with_entities(Issue.status, func.count()).group_by(Issue.status):
        by_status[value] = count

    by_priority = {item.value: 0 for item in IssuePriority}
    for value, count in issues.with_entities(Issue.priority, func.count()).group_by(Issue.priority):
        by_priority[value] = count

    still_open = Issue.status != IssueStatus.closed.value
    open_block = (IssueLink.link_type == IssueLinkType.blocks.value) & (
        IssueLink.source.has(Issue.status != IssueStatus.closed.value)
    )
    return {
        "project": project,
        "issue_count": sum(by_status.values()),
        "by_status": by_status,
        "by_priority": by_priority,
        "overdue_count": issues.filter(
            still_open, Issue.due_date.is_not(None), Issue.due_date < date.today()
        ).count(),
        "unassigned_count": issues.filter(still_open, Issue.assignee_id.is_(None)).count(),
        "blocked_count": issues.filter(still_open, Issue.inbound_links.any(open_block)).count(),
    }


@router.get("/{project_id}/workload", response_model=list[AssigneeWorkload])
def project_workload(project_id: int, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    rows = (
        db.query(Issue.assignee_id, func.count(), func.coalesce(func.sum(Issue.estimate), 0))
        .filter(Issue.project_id == project_id, Issue.status != IssueStatus.closed.value)
        .group_by(Issue.assignee_id)
        .order_by(func.count().desc())
        .all()
    )
    return [
        {"assignee_id": assignee_id, "open_count": count, "estimate_total": estimate}
        for assignee_id, count, estimate in rows
    ]


@router.get("/{project_id}/active-sprint", response_model=SprintRead)
def active_sprint(project_id: int, db: Session = Depends(get_db)) -> Sprint:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    sprint = (
        db.query(Sprint)
        .filter(Sprint.project_id == project_id, Sprint.status == SprintStatus.active.value)
        .first()
    )
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project has no active sprint")
    return sprint


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is None:
        del data["name"]
    if "name" in data:
        clash = db.query(Project).filter(Project.name == data["name"], Project.id != project_id).first()
        if clash:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project name already exists")

    for key, value in data.items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)) -> None:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    db.delete(project)
    db.commit()
