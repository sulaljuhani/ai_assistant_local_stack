"""
Input Validation Middleware

This module provides Pydantic-based validation models for all API endpoints.
It replaces the n8n JavaScript validation with type-safe Python validation.

Usage:
    from middleware.validation import CreateTaskRequest

    @app.post("/api/tasks/create")
    async def create_task(request: CreateTaskRequest):
        # request is automatically validated by FastAPI + Pydantic
        ...
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum
import re


# ============================================================================
# Enums for constrained values
# ============================================================================

class TaskStatus(str, Enum):
    """Task status options"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Task priority levels (1-5)"""
    LOWEST = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    HIGHEST = 5


class ReminderPriority(int, Enum):
    """Reminder priority levels (0-3)"""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    URGENT = 3


class RecurrencePattern(str, Enum):
    """Recurrence patterns"""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class MemorySource(str, Enum):
    """Memory source types"""
    CHAT = "chat"
    CHATGPT = "chatgpt"
    CLAUDE = "claude"
    GEMINI = "gemini"
    ANYTHINGLLM = "anythingllm"


class MemorySector(str, Enum):
    """OpenMemory sector types"""
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    EMOTIONAL = "emotional"
    REFLECTIVE = "reflective"


# ============================================================================
# Task Management Validation Models
# ============================================================================

class CreateTaskRequest(BaseModel):
    """Validation model for creating a task"""
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Task title"
    )
    description: Optional[str] = Field(
        None,
        max_length=5000,
        description="Task description"
    )
    due_date: Optional[datetime] = Field(
        None,
        description="Task due date"
    )
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM,
        description="Task priority (1-5)"
    )
    status: TaskStatus = Field(
        default=TaskStatus.TODO,
        description="Task status"
    )
    category: Optional[str] = Field(
        None,
        max_length=100,
        description="Task category"
    )
    tags: Optional[List[str]] = Field(
        default_factory=list,
        description="Task tags"
    )
    is_recurring: bool = Field(
        default=False,
        description="Whether this is a recurring task"
    )
    recurrence_pattern: Optional[RecurrencePattern] = Field(
        None,
        description="Recurrence pattern"
    )

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure due date is in the future (optional validation)"""
        # Allow past dates for flexibility, but could be enforced if needed
        return v


class UpdateTaskRequest(BaseModel):
    """Validation model for updating a task"""
    model_config = ConfigDict(str_strip_whitespace=True)

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    due_date: Optional[datetime] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    is_recurring: Optional[bool] = None
    recurrence_pattern: Optional[RecurrencePattern] = None


# ============================================================================
# Reminder Validation Models
# ============================================================================

class CreateReminderRequest(BaseModel):
    """Validation model for creating a reminder"""
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Reminder title"
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Reminder description"
    )
    remind_at: datetime = Field(
        ...,
        description="When to fire the reminder"
    )
    priority: ReminderPriority = Field(
        default=ReminderPriority.MEDIUM,
        description="Reminder priority (0-3)"
    )
    category: Optional[str] = Field(
        None,
        max_length=100,
        description="Reminder category"
    )
    recurrence: RecurrencePattern = Field(
        default=RecurrencePattern.NONE,
        description="Recurrence pattern"
    )

    @field_validator('remind_at')
    @classmethod
    def validate_remind_at(cls, v: datetime) -> datetime:
        """Ensure remind_at is in the future"""
        if v <= datetime.now():
            raise ValueError("remind_at must be in the future")
        return v


class UpdateReminderRequest(BaseModel):
    """Validation model for updating a reminder"""
    model_config = ConfigDict(str_strip_whitespace=True)

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    remind_at: Optional[datetime] = None
    priority: Optional[ReminderPriority] = None
    category: Optional[str] = Field(None, max_length=100)
    recurrence: Optional[RecurrencePattern] = None
    is_completed: Optional[bool] = None

    @field_validator('remind_at')
    @classmethod
    def validate_remind_at(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure remind_at is in the future if provided"""
        if v and v <= datetime.now():
            raise ValueError("remind_at must be in the future")
        return v


# ============================================================================
# Event Validation Models
# ============================================================================

class CreateEventRequest(BaseModel):
    """Validation model for creating an event"""
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Event title"
    )
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Event description"
    )
    start_time: datetime = Field(
        ...,
        description="Event start time"
    )
    end_time: datetime = Field(
        ...,
        description="Event end time"
    )
    location: Optional[str] = Field(
        None,
        max_length=500,
        description="Event location"
    )
    category: Optional[str] = Field(
        None,
        max_length=100,
        description="Event category"
    )
    attendees: Optional[List[str]] = Field(
        default_factory=list,
        description="Event attendees"
    )
    is_all_day: bool = Field(
        default=False,
        description="Whether this is an all-day event"
    )

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v: datetime, info) -> datetime:
        """Ensure end_time is after start_time"""
        start_time = info.data.get('start_time')
        if start_time and v <= start_time:
            raise ValueError("end_time must be after start_time")
        return v


class UpdateEventRequest(BaseModel):
    """Validation model for updating an event"""
    model_config = ConfigDict(str_strip_whitespace=True)

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=100)
    attendees: Optional[List[str]] = None
    is_all_day: Optional[bool] = None


# ============================================================================
# OpenMemory Validation Models
# ============================================================================

class StoreChatTurnRequest(BaseModel):
    """Validation model for storing a chat turn in OpenMemory"""
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User identifier"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Conversation UUID (auto-generated if not provided)"
    )
    conversation_title: str = Field(
        default="Untitled Conversation",
        max_length=200,
        description="Conversation title"
    )
    role: Literal["user", "assistant", "system"] = Field(
        ...,
        description="Message role"
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Message content"
    )
    source: MemorySource = Field(
        default=MemorySource.CHAT,
        description="Memory source"
    )
    salience_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Initial salience score (0.0-1.0)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    @field_validator('conversation_id')
    @classmethod
    def validate_uuid(cls, v: Optional[str]) -> Optional[str]:
        """Validate UUID format if provided"""
        if v:
            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            if not re.match(uuid_pattern, v, re.IGNORECASE):
                raise ValueError("conversation_id must be a valid UUID")
        return v


class SearchMemoriesRequest(BaseModel):
    """Validation model for searching memories"""
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query"
    )
    user_id: Optional[str] = Field(
        None,
        max_length=100,
        description="Filter by user ID"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Filter by conversation ID"
    )
    sector: Optional[MemorySector] = Field(
        None,
        description="Filter by memory sector"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of results to return"
    )
    summarize: bool = Field(
        default=False,
        description="Whether to summarize results with LLM"
    )
    min_salience: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum salience score filter"
    )


# ============================================================================
# Document & Vault Validation Models
# ============================================================================

class EmbedDocumentRequest(BaseModel):
    """Validation model for embedding a document"""
    model_config = ConfigDict(str_strip_whitespace=True)

    file_path: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Absolute path to the document"
    )
    file_type: Literal["txt", "md", "pdf", "json"] = Field(
        ...,
        description="Document file type"
    )
    collection_name: str = Field(
        default="knowledge_base",
        description="Qdrant collection name"
    )
    chunk_size: int = Field(
        default=1000,
        ge=100,
        le=5000,
        description="Chunk size for document splitting"
    )
    chunk_overlap: int = Field(
        default=200,
        ge=0,
        le=1000,
        description="Overlap between chunks"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class ReembedFileRequest(BaseModel):
    """Validation model for re-embedding a vault file"""
    model_config = ConfigDict(str_strip_whitespace=True)

    file_path: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Absolute path to the file"
    )
    file_hash: Optional[str] = Field(
        None,
        description="SHA256 hash of the file for change detection"
    )
    force: bool = Field(
        default=False,
        description="Force re-embedding even if hash unchanged"
    )


# ============================================================================
# Import Validation Models
# ============================================================================

class ImportChatExportRequest(BaseModel):
    """Validation model for importing chat exports"""
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User identifier for imported memories"
    )
    source: MemorySource = Field(
        ...,
        description="Source of the export (claude, chatgpt, gemini)"
    )
    default_salience: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Default salience score for imported memories"
    )
    skip_duplicates: bool = Field(
        default=True,
        description="Skip duplicate conversations"
    )


# ============================================================================
# External Service Sync Validation Models
# ============================================================================

class TodoistSyncConfig(BaseModel):
    """Configuration for Todoist sync"""
    api_key: str = Field(..., min_length=1, description="Todoist API key")
    sync_completed: bool = Field(default=False, description="Sync completed tasks")
    sync_interval_minutes: int = Field(default=15, ge=5, le=60)


class GoogleCalendarSyncConfig(BaseModel):
    """Configuration for Google Calendar sync"""
    credentials_path: str = Field(..., description="Path to Google credentials JSON")
    calendar_id: str = Field(default="primary", description="Calendar ID to sync")
    sync_days_ahead: int = Field(default=30, ge=1, le=365, description="Days to sync ahead")
    sync_interval_minutes: int = Field(default=15, ge=5, le=60)


# ============================================================================
# Common Response Models
# ============================================================================

class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: str
    details: Optional[List[str]] = None


# ============================================================================
# Validation Helpers
# ============================================================================

def validate_days_ago(days_ago: Optional[int]) -> int:
    """Validate days_ago parameter (used in multiple tools)"""
    if days_ago is None:
        return 7
    if days_ago < 0:
        raise ValueError("days_ago must be non-negative")
    if days_ago > 365:
        raise ValueError("days_ago must not exceed 365")
    return days_ago


def validate_limit(limit: int, max_limit: int = 100) -> int:
    """Validate limit parameter"""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if limit > max_limit:
        raise ValueError(f"limit must not exceed {max_limit}")
    return limit


def validate_rating(rating: Optional[int]) -> Optional[int]:
    """Validate rating (1-5 scale)"""
    if rating is not None and (rating < 1 or rating > 5):
        raise ValueError("rating must be between 1 and 5")
    return rating
