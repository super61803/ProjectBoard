from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.members import require_project_member
from app.database import get_db
from app.models import Issue, IssueWatcher
from app.schemas import WatcherCreate, WatcherRead

router = APIRouter(tags=["watchers"])


def _find_watcher(db: Session, issue_id: int, user_id: int) -> IssueWatcher | None:
    return (
        db.query(IssueWatcher)
        .filter(IssueWatcher.issue_id == issue_id, IssueWatcher.user_id == user_id)
        .first()
    )


def ensure_watcher(db: Session, issue_id: int, user_id: int) -> IssueWatcher:
    watcher = _find_watcher(db, issue_id, user_id)
    if watcher is None:
        watcher = IssueWatcher(issue_id=issue_id, user_id=user_id)
        db.add(watcher)
    return watcher


@router.get("/issues/{issue_id}/watchers", response_model=list[WatcherRead])
def list_watchers(issue_id: int, db: Session = Depends(get_db)) -> list[IssueWatcher]:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return db.query(IssueWatcher).filter(IssueWatcher.issue_id == issue_id).order_by(IssueWatcher.id).all()


@router.post("/issues/{issue_id}/watchers", response_model=WatcherRead, status_code=status.HTTP_201_CREATED)
def watch_issue(issue_id: int, payload: WatcherCreate, db: Session = Depends(get_db)) -> IssueWatcher:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    require_project_member(db, issue.project_id, payload.user_id)

    if _find_watcher(db, issue_id, payload.user_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already watching this issue")

    watcher = IssueWatcher(issue_id=issue_id, user_id=payload.user_id)
    db.add(watcher)
    db.commit()
    db.refresh(watcher)
    return watcher


@router.delete("/issues/{issue_id}/watchers/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def unwatch_issue(issue_id: int, user_id: int, db: Session = Depends(get_db)) -> None:
    watcher = _find_watcher(db, issue_id, user_id)
    if not watcher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watcher not found")
    db.delete(watcher)
    db.commit()
