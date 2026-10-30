from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Issue, IssueStatus, Project, Story, StoryStatus
from app.schemas import StoryCreate, StoryProgress, StoryRead, StoryUpdate

router = APIRouter(prefix="/stories", tags=["stories"])


@router.get("", response_model=list[StoryRead])
def list_stories(
    response: Response,
    project_id: int | None = Query(default=None),
    status_filter: StoryStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Story]:
    query = db.query(Story)
    if project_id is not None:
        query = query.filter(Story.project_id == project_id)
    if status_filter is not None:
        query = query.filter(Story.status == status_filter.value)
    if q:
        query = query.filter(Story.title.ilike(f"%{q}%"))
    response.headers["X-Total-Count"] = str(query.count())
    return query.order_by(Story.id.desc()).offset(offset).limit(limit).all()


@router.post("", response_model=StoryRead, status_code=status.HTTP_201_CREATED)
def create_story(payload: StoryCreate, db: Session = Depends(get_db)) -> Story:
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    story = Story(
        project_id=payload.project_id,
        title=payload.title,
        description=payload.description,
        status=payload.status.value,
        points=payload.points,
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


@router.get("/{story_id}", response_model=StoryRead)
def get_story(story_id: int, db: Session = Depends(get_db)) -> Story:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
    return story


@router.get("/{story_id}/progress", response_model=StoryProgress)
def story_progress(story_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    issues = db.query(Issue).filter(Issue.story_id == story_id).all()
    closed = [issue for issue in issues if issue.status == IssueStatus.closed.value]
    estimate_total = sum(issue.estimate or 0 for issue in issues)
    estimate_done = sum(issue.estimate or 0 for issue in closed)
    if estimate_total:
        percent = round(estimate_done * 100 / estimate_total)
    elif issues:
        percent = round(len(closed) * 100 / len(issues))
    else:
        percent = 0
    return {
        "story": story,
        "issue_count": len(issues),
        "closed_count": len(closed),
        "estimate_total": estimate_total,
        "estimate_done": estimate_done,
        "percent_complete": percent,
    }


@router.patch("/{story_id}", response_model=StoryRead)
def update_story(story_id: int, payload: StoryUpdate, db: Session = Depends(get_db)) -> Story:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    data = payload.model_dump(exclude_unset=True)
    for required in ("title", "status"):
        if required in data and data[required] is None:
            del data[required]
    if "status" in data and data["status"] is not None:
        data["status"] = data["status"].value

    for key, value in data.items():
        setattr(story, key, value)

    db.commit()
    db.refresh(story)
    return story


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_story(story_id: int, db: Session = Depends(get_db)) -> None:
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
    db.delete(story)
    db.commit()
