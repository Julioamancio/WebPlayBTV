from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Auth schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefresh(BaseModel):
    refresh_token: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# License schemas
class LicenseBase(BaseModel):
    plan_name: str
    max_devices: int = 1

class LicenseCreate(LicenseBase):
    pass

class LicenseResponse(LicenseBase):
    id: int
    license_key: str
    user_id: int
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Device schemas
class DeviceBase(BaseModel):
    device_id: str
    device_name: Optional[str] = None

class DeviceCreate(DeviceBase):
    license_id: int

class DeviceResponse(DeviceBase):
    id: int
    user_id: int
    license_id: int
    is_active: bool
    last_seen: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Channel schemas
class ChannelBase(BaseModel):
    name: str
    url: str
    logo_url: Optional[str] = None
    category: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None

class ChannelResponse(ChannelBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True