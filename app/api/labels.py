from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Issue, Label, Project
from app.schemas import IssueLabelAttach, IssueRead, LabelCreate, LabelRead

router = APIRouter(tags=["labels"])


@router.get("/projects/{project_id}/labels", response_model=list[LabelRead])
def list_labels(project_id: int, db: Session = Depends(get_db)) -> list[Label]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return db.query(Label).filter(Label.project_id == project_id).order_by(Label.name).all()


@router.post("/projects/{project_id}/labels", response_model=LabelRead, status_code=status.HTTP_201_CREATED)
def create_label(project_id: int, payload: LabelCreate, db: Session = Depends(get_db)) -> Label:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    existing = db.query(Label).filter(Label.project_id == project_id, Label.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Label name already exists")

    label = Label(project_id=project_id, name=payload.name, color=payload.color)
    db.add(label)
    db.commit()
    db.refresh(label)
    return label


@router.delete("/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_label(label_id: int, db: Session = Depends(get_db)) -> None:
    label = db.get(Label, label_id)
    if not label:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label not found")
    db.delete(label)
    db.commit()


@router.post("/issues/{issue_id}/labels", response_model=IssueRead)
def attach_label(issue_id: int, payload: IssueLabelAttach, db: Session = Depends(get_db)) -> Issue:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    label = db.get(Label, payload.label_id)
    if not label or label.project_id != issue.project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Label does not belong to project")
    if label in issue.labels:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Label already attached")

    issue.labels.append(label)
    db.commit()
    db.refresh(issue)
    return issue


@router.delete("/issues/{issue_id}/labels/{label_id}", response_model=IssueRead)
def detach_label(issue_id: int, label_id: int, db: Session = Depends(get_db)) -> Issue:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    label = db.get(Label, label_id)
    if not label or label not in issue.labels:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label is not attached")

    issue.labels.remove(label)
    db.commit()
    db.refresh(issue)
    return issue
