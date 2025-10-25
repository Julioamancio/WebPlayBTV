from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase, ORMModel):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LicenseBase(BaseModel):
    plan_name: str
    max_devices: int = 1


class LicenseCreate(LicenseBase):
    pass


class LicenseResponse(LicenseBase, ORMModel):
    id: int
    license_key: str
    user_id: int
    is_active: bool
    expires_at: Optional[datetime]
    issued_at: Optional[datetime]
    approved_by: Optional[int]
    request_id: Optional[int]
    created_at: datetime


class LicenseDetailedResponse(LicenseResponse):
    devices: List["DeviceResponse"] = Field(default_factory=list)


class LicenseRequestCreate(BaseModel):
    plan_name: str
    device_id: str
    device_name: Optional[str] = None
    device_info: Optional[str] = None
    notes: Optional[str] = None


class LicenseRequestResponse(ORMModel):
    id: int
    plan_name: str
    max_devices: int
    status: str
    device_id: str
    device_name: Optional[str]
    device_info: Optional[str]
    notes: Optional[str]
    admin_notes: Optional[str]
    device_secret: Optional[str]
    requested_at: datetime
    decided_at: Optional[datetime]


class LicenseRequestAdminResponse(LicenseRequestResponse):
    user_id: int
    user_email: Optional[str] = None


class DeviceBase(BaseModel):
    device_id: str
    device_name: Optional[str] = None


class DeviceCreate(DeviceBase):
    license_id: int


class DeviceResponse(DeviceBase, ORMModel):
    id: int
    user_id: int
    license_id: int
    is_active: bool
    hardware_info: Optional[str]
    last_seen: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]


class DeviceWithSecret(DeviceResponse):
    device_secret: Optional[str] = None


class LicenseApprovalResult(BaseModel):
    license: LicenseResponse
    device: DeviceWithSecret


class ChannelBase(BaseModel):
    name: str
    url: str
    logo_url: Optional[str] = None
    category: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None


class ChannelResponse(ChannelBase, ORMModel):
    id: int
    is_active: bool
    created_at: datetime
    user_id: int
    playlist_id: Optional[int] = None


class DeviceUnbind(BaseModel):
    id: int


class DeviceHeartbeat(BaseModel):
    device_id: str
    device_secret: Optional[str] = None


class M3UPlaylistResponse(ORMModel):
    id: int
    name: str
    url: Optional[str] = None
    content: Optional[str] = None
    channels_count: int
    last_updated: Optional[datetime]
    is_active: bool
    created_at: datetime
    user_id: int


class M3UPlaylistUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    is_active: Optional[bool] = None


class AdminNotificationResponse(ORMModel):
    id: int
    type: str
    message: str
    payload: Optional[str]
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime]


class LicenseApproval(BaseModel):
    expires_in_days: int = 30
    admin_notes: Optional[str] = None


class LicenseRejection(BaseModel):
    admin_notes: Optional[str] = None

