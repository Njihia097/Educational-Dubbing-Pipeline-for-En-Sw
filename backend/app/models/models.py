import uuid
from datetime import datetime
from sqlalchemy.sql import func
from sqlalchemy import (
    Column, String, Text, DateTime, JSON, Enum, ForeignKey, Boolean, Numeric, CheckConstraint, Index, Enum as ENUM, TIMESTAMP, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import db

class AppUser(db.Model):
    __tablename__ = "app_user"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, unique=True, nullable=False)
    display_name = Column(Text)
    password_hash = Column(Text, nullable=False)
    role = Column(Text, default="creator")
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    projects = relationship("Project", backref="owner", cascade="all,delete")

class Project(db.Model):
    __tablename__ = "project"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"))
    name = Column(Text, nullable=False)
    meta = Column(JSON, default={})
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (Index("idx_project_owner", "owner_id"),)


class Asset(db.Model):
    __tablename__ = "asset"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id"))

    kind = Column(Text, nullable=False)
    uri = Column(Text, nullable=False)
    duration_sec = Column(Numeric)
    meta = Column(JSON, default={})
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (
    CheckConstraint("kind IN ('video','audio','subtitle','text')"),
    Index("idx_asset_owner", "owner_id"),
    Index("idx_asset_project", "project_id"),
    )


class Job(db.Model):
    __tablename__ = "job"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = db.Column(UUID(as_uuid=True), db.ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey("project.id"))
    input_asset_id = db.Column(UUID(as_uuid=True), db.ForeignKey("asset.id"))
    state = db.Column(ENUM("queued", "running", "succeeded", "failed", "cancelled", name="job_status"), nullable=False, default="queued")
    error_code = db.Column(Text)
    model_version = db.Column(Text)
    meta = db.Column(JSONB, nullable=False, default=dict)
    current_step = db.Column(Text)
    progress = db.Column(db.Float)
    created_at = db.Column(TIMESTAMP(timezone=True), nullable=False, server_default=db.func.now())
    started_at = db.Column(TIMESTAMP(timezone=True))
    finished_at = db.Column(TIMESTAMP(timezone=True))
    __table_args__ = (
        Index("idx_job_owner", "owner_id"),
        Index("idx_job_state", "state"),
        Index("idx_job_created", "created_at"),
        db.UniqueConstraint('input_asset_id', name='unique_job_input'),
    )

class JobStep(db.Model):
    __tablename__ = "job_step"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = db.Column(UUID(as_uuid=True), db.ForeignKey("job.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(Text, nullable=False)
    state = db.Column(Text, nullable=False, default="pending")
    started_at = db.Column(TIMESTAMP(timezone=True))
    finished_at = db.Column(TIMESTAMP(timezone=True))
    metrics = db.Column(JSONB, nullable=False, default=dict)
    log_ref = db.Column(Text)
    __table_args__ = (
        Index("idx_jobstep_job", "job_id"),
    )

class JobOutput(db.Model):
    __tablename__ = "job_output"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = db.Column(UUID(as_uuid=True), db.ForeignKey("job.id", ondelete="CASCADE"), nullable=False)
    kind = db.Column(Text, nullable=False)
    asset_id = db.Column(UUID(as_uuid=True), db.ForeignKey("asset.id"))
    meta = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(TIMESTAMP(timezone=True), nullable=False, server_default=db.func.now())
    __table_args__ = (
        CheckConstraint("kind IN ('translated_text','tts_audio','lipsynced_video','subtitle')"),
        Index("idx_joboutput_job", "job_id"),
    )

class Feedback(db.Model):
    __tablename__ = "feedback"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = db.Column(UUID(as_uuid=True), db.ForeignKey("job.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("app_user.id"))
    verdict = db.Column(Text, nullable=False)
    comment = db.Column(Text)
    meta = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(TIMESTAMP(timezone=True), nullable=False, server_default=db.func.now())
    __table_args__ = (
        CheckConstraint("verdict IN ('approve','reject','edit')"),
        Index("idx_feedback_job", "job_id"),
    )

class DatasetQueue(db.Model):
    __tablename__ = "dataset_queue"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = db.Column(UUID(as_uuid=True), db.ForeignKey("job.id", ondelete="CASCADE"), nullable=False)
    sample_ref = db.Column(Text)
    lang_pair = db.Column(Text)
    approved = db.Column(Boolean, default=False)
    created_at = db.Column(TIMESTAMP(timezone=True), nullable=False, server_default=db.func.now())

class AnalyticsEvent(db.Model):
    __tablename__ = "analytics_event"
    id = db.Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("app_user.id"))
    job_id = db.Column(UUID(as_uuid=True), db.ForeignKey("job.id"))
    event_name = db.Column(Text, nullable=False)
    event_ts = db.Column(TIMESTAMP(timezone=True), nullable=False, server_default=db.func.now())
    payload = db.Column(JSONB, nullable=False, default=dict)
    __table_args__ = (
        Index("idx_analytics_event_name", "event_name"),
        Index("idx_analytics_event_ts", "event_ts"),
    )
