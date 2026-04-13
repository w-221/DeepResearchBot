# models.py - Pydantic 数据模型定义
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum


class UserStatus(str, Enum):
    """用户状态枚举"""
    ACTIVE = "active"
    LOCKED = "locked"
    DISABLED = "disabled"
    DELETED = "deleted"


class RegisterRequest(BaseModel):
    """用户注册请求模型"""
    email: EmailStr = Field(..., description="员工邮箱", min_length=6, max_length=128)
    password: str = Field(..., description="登录密码", min_length=6, max_length=50)
    name: Optional[str] = Field(None, max_length=64, description="员工姓名")
    department: Optional[str] = Field(None, max_length=64, description="所属部门")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    employee_id: Optional[str] = Field(None, max_length=32, description="员工工号")

    @validator('password')
    def validate_password(cls, v):
        """验证密码强度"""
        if len(v) < 6:
            raise ValueError('密码长度不能少于6位')
        # 可以添加更复杂的密码验证规则
        return v

    @validator('phone')
    def validate_phone(cls, v):
        """验证手机号格式"""
        if v and not v.isdigit():
            raise ValueError('手机号必须是数字')
        return v


class LoginRequest(BaseModel):
    """用户登录请求模型"""
    email: str = Field(..., description="员工邮箱")
    password: str = Field(..., description="登录密码", min_length=6, max_length=50)


class VerifyCodeLoginRequest(BaseModel):
    """验证码登录请求模型"""
    email: EmailStr = Field(..., description="员工邮箱")
    code: str = Field(..., description="验证码", min_length=6, max_length=10)


class SendCodeRequest(BaseModel):
    """发送验证码请求模型"""
    email: EmailStr = Field(..., description="员工邮箱")


class UserInfo(BaseModel):
    """用户信息响应模型"""
    id: int
    email: str
    name: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    employee_id: Optional[str] = None
    is_admin: bool = False
    last_login_at: Optional[datetime] = None
    status: UserStatus


class LoginData(BaseModel):
    """登录数据模型"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


class AuthResponse(BaseModel):
    """认证响应基类"""
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None


class RegisterResponse(AuthResponse):
    """注册响应模型"""
    pass


class LoginResponse(AuthResponse):
    """登录响应模型（覆盖 AuthResponse）"""
    data: Optional[LoginData] = None


class ErrorResponse(AuthResponse):
    """错误响应模型"""
    code: int
    message: str
    data: None = None


class EmployeeDB(BaseModel):
    """数据库员工信息模型"""
    id: Optional[int] = None
    email: str
    password_hash: str
    salt: Optional[str] = None
    employee_id: Optional[str] = None
    name: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE
    is_admin: int = 0
    failed_login_count: int = 0
    lock_until: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    verification_code: Optional[str] = None
    verification_code_sent_at: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None
    verification_code_failed_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # 允许从 ORM 对象创建


class VerificationCodeInfo(BaseModel):
    """验证码信息模型"""
    code: str
    email: str
    expiry_minutes: int = 5


# 密码强度验证
def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    验证密码强度

    Returns:
        (is_valid, message)
    """
    if len(password) < 6:
        return False, "密码长度不能少于6位"
    if len(password) > 50:
        return False, "密码长度不能超过50位"

    # 检查是否包含数字
    has_digit = any(c.isdigit() for c in password)

    # 检查是否包含字母
    has_letter = any(c.isalpha() for c in password)

    # 检查是否包含特殊字符
    has_special = any(not c.isalnum() for c in password)

    # 基本规则：至少包含数字和字母
    if not (has_digit and has_letter):
        return False, "密码必须包含数字和字母"

    return True, "密码强度符合要求"