from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import IssuePriority, IssueStatus, MemberRole, StoryStatus


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
    assignee_id: int | None = None


class IssueUpdate(BaseModel):
    story_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: IssueStatus | None = None
    priority: IssuePriority | None = None
    assignee_id: int | None = None


class IssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    story_id: int | None
    title: str
    description: str | None
    status: str
    priority: str
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    display_name: str = Field(min_length=1, max_length=120)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    created_at: datetime


class MemberCreate(BaseModel):
    user_id: int
    role: MemberRole = MemberRole.member


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    role: str
    created_at: datetime


class CommentCreate(BaseModel):
    author_id: int
    body: str = Field(min_length=1)


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    issue_id: int
    author_id: int
    body: str
    created_at: datetime
    updated_at: datetime
