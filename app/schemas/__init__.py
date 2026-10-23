from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import IssueLinkType, IssuePriority, IssueStatus, MemberRole, StoryStatus


class ProjectCreate(BaseModel):
    key: str = Field(min_length=2, max_length=10, pattern=r"^[A-Za-z][A-Za-z0-9]+$")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class ProjectSummary(BaseModel):
    project: ProjectRead
    issue_count: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    overdue_count: int
    unassigned_count: int
    blocked_count: int


class AssigneeWorkload(BaseModel):
    assignee_id: int | None
    open_count: int
    estimate_total: int


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


class StoryProgress(BaseModel):
    story: StoryRead
    issue_count: int
    closed_count: int
    estimate_total: int
    estimate_done: int
    percent_complete: int


class LabelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    color: str = Field(default="#6B7280", min_length=4, max_length=7)


class LabelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    color: str | None = Field(default=None, min_length=4, max_length=7)


class LabelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    color: str
    created_at: datetime


class LabelUsage(BaseModel):
    label: LabelRead
    issue_count: int
    open_count: int


class IssueLabelAttach(BaseModel):
    label_id: int


class IssueCreate(BaseModel):
    project_id: int
    story_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: IssueStatus = IssueStatus.open
    priority: IssuePriority = IssuePriority.medium
    assignee_id: int | None = None
    sprint_id: int | None = None
    estimate: int | None = Field(default=None, ge=0)
    due_date: date | None = None
    actor_id: int | None = None


class IssueUpdate(BaseModel):
    story_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: IssueStatus | None = None
    priority: IssuePriority | None = None
    assignee_id: int | None = None
    sprint_id: int | None = None
    estimate: int | None = Field(default=None, ge=0)
    due_date: date | None = None
    actor_id: int | None = None


class IssueBulkUpdate(BaseModel):
    issue_ids: list[int] = Field(min_length=1, max_length=100)
    status: IssueStatus | None = None
    priority: IssuePriority | None = None
    assignee_id: int | None = None
    sprint_id: int | None = None
    actor_id: int | None = None


class IssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    number: int
    key: str
    story_id: int | None
    title: str
    description: str | None
    status: str
    priority: str
    assignee_id: int | None
    sprint_id: int | None
    estimate: int | None
    due_date: date | None
    labels: list[LabelRead] = []
    created_at: datetime
    updated_at: datetime


class IssueLinkCreate(BaseModel):
    target_id: int
    link_type: IssueLinkType
    actor_id: int | None = None


class IssueLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    target_id: int
    link_type: str
    created_at: datetime


class IssueDetail(IssueRead):
    links: list[IssueLinkRead] = []


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    display_name: str = Field(min_length=1, max_length=120)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    created_at: datetime


class UserWork(BaseModel):
    user: UserRead
    assigned: list[IssueRead]
    watching: list[IssueRead]


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


class SprintCreate(BaseModel):
    project_id: int
    name: str = Field(min_length=1, max_length=120)
    goal: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class SprintUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    goal: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class SprintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    goal: str | None
    status: str
    start_date: date | None
    end_date: date | None
    created_at: datetime
    updated_at: datetime


class SprintBoard(BaseModel):
    sprint: SprintRead
    columns: dict[str, list[IssueRead]]


class SprintProgress(BaseModel):
    sprint: SprintRead
    issue_count: int
    closed_count: int
    estimate_total: int
    estimate_done: int
    estimate_remaining: int


class BurndownPoint(BaseModel):
    day: date
    remaining: int


class SprintBurndown(BaseModel):
    sprint: SprintRead
    estimate_total: int
    points: list[BurndownPoint]


class CommentCreate(BaseModel):
    author_id: int
    body: str = Field(min_length=1)


class CommentUpdate(BaseModel):
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


class WatcherCreate(BaseModel):
    user_id: int


class WatcherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    issue_id: int
    user_id: int
    created_at: datetime


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    issue_id: int
    actor_id: int | None
    action: str
    field: str | None
    old_value: str | None
    new_value: str | None
    created_at: datetime
