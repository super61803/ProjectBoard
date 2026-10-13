from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.activity import record_activity
from app.api.members import require_project_member
from app.api.watchers import ensure_watcher
from app.database import get_db
from app.models import ActivityAction, Comment, Issue
from app.schemas import CommentCreate, CommentRead, CommentUpdate

router = APIRouter(tags=["comments"])


@router.get("/issues/{issue_id}/comments", response_model=list[CommentRead])
def list_comments(issue_id: int, db: Session = Depends(get_db)) -> list[Comment]:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return db.query(Comment).filter(Comment.issue_id == issue_id).order_by(Comment.id).all()


@router.post("/issues/{issue_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def create_comment(issue_id: int, payload: CommentCreate, db: Session = Depends(get_db)) -> Comment:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    require_project_member(db, issue.project_id, payload.author_id)

    comment = Comment(issue_id=issue_id, author_id=payload.author_id, body=payload.body)
    db.add(comment)
    record_activity(
        db,
        issue_id,
        ActivityAction.commented,
        actor_id=payload.author_id,
        new_value=payload.body,
    )
    ensure_watcher(db, issue_id, payload.author_id)
    db.commit()
    db.refresh(comment)
    return comment


@router.patch("/comments/{comment_id}", response_model=CommentRead)
def update_comment(comment_id: int, payload: CommentUpdate, db: Session = Depends(get_db)) -> Comment:
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    if comment.author_id != payload.author_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the author can edit a comment")

    if comment.body != payload.body:
        record_activity(
            db,
            comment.issue_id,
            ActivityAction.comment_edited,
            actor_id=payload.author_id,
            old_value=comment.body,
            new_value=payload.body,
        )
    comment.body = payload.body
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: int,
    actor_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> None:
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    record_activity(
        db,
        comment.issue_id,
        ActivityAction.comment_deleted,
        actor_id=actor_id,
        old_value=comment.body,
    )
    db.delete(comment)
    db.commit()
