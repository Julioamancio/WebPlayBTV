from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    licenses = relationship("License", back_populates="user", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    playlists = relationship("M3UPlaylist", back_populates="user", cascade="all, delete-orphan")
    channels = relationship("Channel", back_populates="user", cascade="all, delete-orphan")
    license_requests = relationship(
        "LicenseRequest", back_populates="user", cascade="all, delete-orphan"
    )
    admin_notifications = relationship(
        "AdminNotification", back_populates="admin", cascade="all, delete-orphan"
    )


class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    license_key = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_name = Column(String, nullable=False)
    max_devices = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    request_id = Column(Integer, ForeignKey("license_requests.id"), nullable=True, index=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    stripe_subscription_id = Column(String, nullable=True)
    stripe_customer_id = Column(String, nullable=True)

    user = relationship("User", back_populates="licenses")
    devices = relationship("Device", back_populates="license", cascade="all, delete-orphan")
    request = relationship("LicenseRequest", back_populates="license", uselist=False)
    approver = relationship("User", foreign_keys=[approved_by])


class LicenseRequest(Base):
    __tablename__ = "license_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_name = Column(String, nullable=False)
    max_devices = Column(Integer, default=1)
    status = Column(String, nullable=False, default="pending", index=True)
    device_id = Column(String, nullable=False)
    device_name = Column(String, nullable=True)
    device_info = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    device_secret = Column(String, nullable=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", back_populates="license_requests", foreign_keys=[user_id])
    license = relationship("License", back_populates="request")
    admin = relationship("User", foreign_keys=[decided_by])


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    device_name = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    license_id = Column(Integer, ForeignKey("licenses.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    secret_hash = Column(String, nullable=True)
    hardware_info = Column(Text, nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="devices")
    license = relationship("License", back_populates="devices")


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(Text, nullable=False)
    logo_url = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    country = Column(String, nullable=True)
    language = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    playlist_id = Column(Integer, ForeignKey("m3u_playlists.id"), nullable=True, index=True)

    user = relationship("User", back_populates="channels")
    playlist = relationship("M3UPlaylist", back_populates="channels")


class M3UPlaylist(Base):
    __tablename__ = "m3u_playlists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    channels_count = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    user = relationship("User", back_populates="playlists")
    channels = relationship("Channel", back_populates="playlist", cascade="all, delete-orphan")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AdminNotification(Base):
    __tablename__ = "admin_notifications"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    payload = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)

    admin = relationship("User", back_populates="admin_notifications")

