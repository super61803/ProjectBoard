from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Issue, IssueStatus, IssueWatcher, MemberRole, Project, ProjectMember, User
from app.schemas import MemberCreate, MemberRead, MemberUpdate, UserCreate, UserRead, UserWork

router = APIRouter(tags=["members"])


def require_project_member(db: Session, project_id: int, user_id: int) -> ProjectMember:
    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not a project member")
    return membership


def _ensure_other_owner(db: Session, membership: ProjectMember) -> None:
    if membership.role != MemberRole.owner.value:
        return
    owners = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == membership.project_id, ProjectMember.role == MemberRole.owner.value)
        .count()
    )
    if owners <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project must keep at least one owner")


@router.get("/users", response_model=list[UserRead])
def list_users(
    response: Response,
    q: str | None = Query(default=None, min_length=1),
    project_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[User]:
    query = db.query(User)
    if project_id is not None:
        members = select(ProjectMember.user_id).where(ProjectMember.project_id == project_id)
        query = query.filter(User.id.in_(members))
    if q:
        pattern = f"%{q}%"
        query = query.filter(or_(User.email.ilike(pattern), User.display_name.ilike(pattern)))
    response.headers["X-Total-Count"] = str(query.count())
    return query.order_by(User.id.desc()).offset(offset).limit(limit).all()


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    existing = db.query(User).filter(func.lower(User.email) == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    user = User(email=payload.email, display_name=payload.display_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/{user_id}/work", response_model=UserWork)
def user_work(user_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    open_issues = db.query(Issue).filter(Issue.status != IssueStatus.closed.value)
    by_due_date = (Issue.due_date.asc().nulls_last(), Issue.id.desc())
    assigned = open_issues.filter(Issue.assignee_id == user_id).order_by(*by_due_date).all()
    watching = (
        open_issues.filter(
            Issue.watchers.any(IssueWatcher.user_id == user_id),
            or_(Issue.assignee_id.is_(None), Issue.assignee_id != user_id),
        )
        .order_by(*by_due_date)
        .all()
    )
    return {"user": user, "assigned": assigned, "watching": watching}


@router.get("/projects/{project_id}/members", response_model=list[MemberRead])
def list_members(
    project_id: int,
    role: MemberRole | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ProjectMember]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    query = db.query(ProjectMember).filter(ProjectMember.project_id == project_id)
    if role is not None:
        query = query.filter(ProjectMember.role == role.value)
    return query.order_by(ProjectMember.id).all()


@router.post("/projects/{project_id}/members", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
def add_member(project_id: int, payload: MemberCreate, db: Session = Depends(get_db)) -> ProjectMember:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == payload.user_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a project member")

    membership = ProjectMember(project_id=project_id, user_id=payload.user_id, role=payload.role.value)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


@router.patch("/projects/{project_id}/members/{user_id}", response_model=MemberRead)
def update_member(project_id: int, user_id: int, payload: MemberUpdate, db: Session = Depends(get_db)) -> ProjectMember:
    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    if payload.role.value != membership.role:
        _ensure_other_owner(db, membership)
        membership.role = payload.role.value
        db.commit()
        db.refresh(membership)
    return membership


@router.delete("/projects/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(project_id: int, user_id: int, db: Session = Depends(get_db)) -> None:
    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    _ensure_other_owner(db, membership)
    db.delete(membership)
    db.commit()
