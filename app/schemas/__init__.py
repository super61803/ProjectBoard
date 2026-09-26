from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import IssuePriority, IssueStatus, StoryStatus


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class StoryCreate(BaseModel):
    project_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: StoryStatus = StoryStatus.backlog
    points: int | None = Field(default=None, ge=0)


class StoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: StoryStatus | None = None
    points: int | None = Field(default=None, ge=0)


class StoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    description: str | None
    status: str
    points: int | None
    created_at: datetime
    updated_at: datetime


class IssueCreate(BaseModel):
    project_id: int
    story_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: IssueStatus = IssueStatus.open
    priority: IssuePriority = IssuePriority.medium


class IssueUpdate(BaseModel):
    story_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: IssueStatus | None = None
    priority: IssuePriority | None = None


class IssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    story_id: int | None
    title: str
    description: str | None
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime
