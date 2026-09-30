from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, Sprint, SprintStatus
from app.schemas import SprintCreate, SprintRead, SprintUpdate

router = APIRouter(prefix="/sprints", tags=["sprints"])


def require_assignable_sprint(db: Session, project_id: int, sprint_id: int) -> Sprint:
    sprint = db.get(Sprint, sprint_id)
    if not sprint or sprint.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sprint does not belong to project")
    if sprint.status == SprintStatus.completed.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot assign issues to a completed sprint")
    return sprint


def _check_dates(start_date: date | None, end_date: date | None) -> None:
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End date must be on or after the start date")


@router.get("", response_model=list[SprintRead])
def list_sprints(project_id: int | None = Query(default=None), db: Session = Depends(get_db)) -> list[Sprint]:
    query = db.query(Sprint)
    if project_id is not None:
        query = query.filter(Sprint.project_id == project_id)
    return query.order_by(Sprint.id.desc()).all()


@router.post("", response_model=SprintRead, status_code=status.HTTP_201_CREATED)
def create_sprint(payload: SprintCreate, db: Session = Depends(get_db)) -> Sprint:
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    _check_dates(payload.start_date, payload.end_date)

    sprint = Sprint(
        project_id=payload.project_id,
        name=payload.name,
        goal=payload.goal,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return sprint


@router.get("/{sprint_id}", response_model=SprintRead)
def get_sprint(sprint_id: int, db: Session = Depends(get_db)) -> Sprint:
    sprint = db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sprint not found")
    return sprint


@router.patch("/{sprint_id}", response_model=SprintRead)
def update_sprint(sprint_id: int, payload: SprintUpdate, db: Session = Depends(get_db)) -> Sprint:
    sprint = db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sprint not found")
    if sprint.status == SprintStatus.completed.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Completed sprints cannot be edited")

    data = payload.model_dump(exclude_unset=True)
    start_date = data["start_date"] if "start_date" in data else sprint.start_date
    end_date = data["end_date"] if "end_date" in data else sprint.end_date
    _check_dates(start_date, end_date)

    for key, value in data.items():
        setattr(sprint, key, value)

    db.commit()
    db.refresh(sprint)
    return sprint


@router.post("/{sprint_id}/start", response_model=SprintRead)
def start_sprint(sprint_id: int, db: Session = Depends(get_db)) -> Sprint:
    sprint = db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sprint not found")
    if sprint.status != SprintStatus.planned.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only a planned sprint can be started")

    active = (
        db.query(Sprint)
        .filter(Sprint.project_id == sprint.project_id, Sprint.status == SprintStatus.active.value)
        .first()
    )
    if active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project already has an active sprint")

    sprint.status = SprintStatus.active.value
    if sprint.start_date is None:
        sprint.start_date = date.today()
    db.commit()
    db.refresh(sprint)
    return sprint


@router.post("/{sprint_id}/complete", response_model=SprintRead)
def complete_sprint(sprint_id: int, db: Session = Depends(get_db)) -> Sprint:
    sprint = db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sprint not found")
    if sprint.status != SprintStatus.active.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only an active sprint can be completed")

    sprint.status = SprintStatus.completed.value
    if sprint.end_date is None:
        sprint.end_date = date.today()
    db.commit()
    db.refresh(sprint)
    return sprint


@router.delete("/{sprint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sprint(sprint_id: int, db: Session = Depends(get_db)) -> None:
    sprint = db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sprint not found")
    if sprint.status != SprintStatus.planned.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only a planned sprint can be deleted")
    db.delete(sprint)
    db.commit()
