from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Activity, Issue
from app.schemas import ActivityRead

router = APIRouter(tags=["activity"])


@router.get("/issues/{issue_id}/activity", response_model=list[ActivityRead])
def list_activity(issue_id: int, db: Session = Depends(get_db)) -> list[Activity]:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return db.query(Activity).filter(Activity.issue_id == issue_id).order_by(Activity.id).all()
