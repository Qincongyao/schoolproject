import json
from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Admin(UserMixin, db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def get_id(self):
        return f"admin-{self.id}"

    @property
    def is_admin(self):
        return True


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    works = db.relationship("Work", backref="submitter", lazy=True)

    def get_id(self):
        return f"user-{self.id}"

    @property
    def is_admin(self):
        return False


class Work(db.Model):
    __tablename__ = "works"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    summary = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    category = db.Column(db.String(32), nullable=False, index=True)
    cover_image = db.Column(db.String(256), nullable=False)
    images = db.Column(db.Text, nullable=False, default="")
    image_captions = db.Column(db.Text, default="")
    tags = db.Column(db.String(256), default="", index=True)

    project_time = db.Column(db.String(64), default="")
    supervisor = db.Column(db.String(64), default="")
    technical_angle = db.Column(db.Text, default="")
    technical_angle_en = db.Column(db.Text, default="")
    summary_en = db.Column(db.Text, default="")
    video_intro = db.Column(db.Text, default="")
    video_intro_en = db.Column(db.Text, default="")
    milestones_en = db.Column(db.Text, default="")
    author_reflection = db.Column(db.Text, default="")
    author_reflection_en = db.Column(db.Text, default="")
    activities_awards = db.Column(db.Text, default="")
    activities_awards_en = db.Column(db.Text, default="")
    activity_images = db.Column(db.Text, default="")

    paper_link = db.Column(db.String(512), default="")
    github_link = db.Column(db.String(512), default="")
    video_link = db.Column(db.String(512), default="")
    ppt_link = db.Column(db.String(512), default="")
    report_links = db.Column(db.Text, default="")

    author_name = db.Column(db.String(64), nullable=False)
    student_id = db.Column(db.String(32), nullable=False)
    grade = db.Column(db.String(64), nullable=False)
    contact = db.Column(db.String(120), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    status = db.Column(db.String(20), default="pending", index=True)
    is_hidden = db.Column(db.Boolean, default=False, index=True)
    admin_note = db.Column(db.Text, default="")
    reject_reason = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    reviewed_at = db.Column(db.DateTime)

    @property
    def image_list(self):
        if not self.images:
            return [self.cover_image] if self.cover_image else []
        return [p for p in self.images.split("|") if p]

    @property
    def image_items(self):
        imgs = self.image_list
        caps = [c.strip() for c in (self.image_captions or "").split("|")]
        while len(caps) < len(imgs):
            caps.append("")
        return list(zip(imgs, caps[: len(imgs)]))

    @property
    def activity_image_list(self):
        if not self.activity_images:
            return []
        return [p for p in self.activity_images.split("|") if p]

    @property
    def tag_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def milestone_list(self):
        if not self.milestones:
            return []
        try:
            data = json.loads(self.milestones)
            if isinstance(data, list):
                return [m for m in data if m.get("title") or m.get("desc")]
        except (json.JSONDecodeError, TypeError):
            pass
        return []

    @property
    def milestone_list_en(self):
        if not self.milestones_en:
            return self.milestone_list
        try:
            data = json.loads(self.milestones_en)
            if isinstance(data, list):
                return [m for m in data if m.get("title") or m.get("desc")]
        except (json.JSONDecodeError, TypeError):
            pass
        return self.milestone_list

    @property
    def report_link_list(self):
        if not self.report_links:
            return []
        return [ln.strip() for ln in self.report_links.splitlines() if ln.strip()]

    def category_label(self, lang="zh"):
        from config import Config

        return Config.category_label(self.category, lang)

    @property
    def is_public(self):
        return self.status == "approved" and not self.is_hidden

    def all_image_paths(self):
        paths = list(self.image_list)
        paths.extend(self.activity_image_list)
        return paths
