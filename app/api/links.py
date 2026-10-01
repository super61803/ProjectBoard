from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Issue, IssueLink
from app.schemas import IssueLinkCreate, IssueLinkRead

router = APIRouter(tags=["links"])


def _existing_link(db: Session, source_id: int, target_id: int, link_type: str) -> IssueLink | None:
    return (
        db.query(IssueLink)
        .filter(
            IssueLink.link_type == link_type,
            or_(
                (IssueLink.source_id == source_id) & (IssueLink.target_id == target_id),
                (IssueLink.source_id == target_id) & (IssueLink.target_id == source_id),
            ),
        )
        .first()
    )


@router.get("/issues/{issue_id}/links", response_model=list[IssueLinkRead])
def list_links(issue_id: int, db: Session = Depends(get_db)) -> list[IssueLink]:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return (
        db.query(IssueLink)
        .filter(or_(IssueLink.source_id == issue_id, IssueLink.target_id == issue_id))
        .order_by(IssueLink.id)
        .all()
    )


@router.post("/issues/{issue_id}/links", response_model=IssueLinkRead, status_code=status.HTTP_201_CREATED)
def create_link(issue_id: int, payload: IssueLinkCreate, db: Session = Depends(get_db)) -> IssueLink:
    source = db.get(Issue, issue_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    target = db.get(Issue, payload.target_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target issue not found")
    if source.id == target.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An issue cannot link to itself")

    if _existing_link(db, source.id, target.id, payload.link_type.value):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="These issues are already linked")

    link = IssueLink(source_id=source.id, target_id=target.id, link_type=payload.link_type.value)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(link_id: int, db: Session = Depends(get_db)) -> None:
    link = db.get(IssueLink, link_id)
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    db.delete(link)
    db.commit()
