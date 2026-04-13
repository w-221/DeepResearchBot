# auth.py - 认证服务模块
import os
import secrets
import bcrypt
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pymysql
from fastapi import APIRouter, HTTPException, Depends, status, Form, Request, Body
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from api.models import (
    RegisterRequest, LoginRequest, VerifyCodeLoginRequest,
    SendCodeRequest, UserStatus, UserInfo,
    LoginData, LoginResponse, RegisterResponse, ErrorResponse,
    EmployeeDB, VerificationCodeInfo,
    validate_password_strength
)
from api.database import execute_query
from api.email_service import send_verification_email
from api.middleware import create_access_token, verify_token, oauth2_scheme, add_token_to_blacklist

# 路由器
auth_router = APIRouter(prefix="/api/auth", tags=["认证"])

# 日志
logger = logging.getLogger(__name__)

# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))  # 7天

# 验证码配置
VERIFICATION_CODE_EXPIRE_MINUTES = 5
MAX_VERIFICATION_CODE_ATTEMPTS = 5
FAILED_LOGIN_LOCK_MINUTES = 30
MAX_FAILED_LOGIN_COUNT = 5


# HTTP 异常
class AuthException(HTTPException):
    def __init__(self, code: int, message: str):
        super().__init__(status_code=code, detail=message)


# 辅助函数
def hash_password(password: str) -> str:
    """哈希密码（bcrypt）"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error(f"密码验证失败: {e}")
        return False


def generate_verification_code() -> str:
    """生成6位数字验证码"""
    return ''.join(secrets.choice('0123456789') for _ in range(6))


async def check_email_exists(email: str) -> bool:
    """检查邮箱是否已存在"""
    try:
        result = execute_query(
            "SELECT id FROM employee_login_info WHERE email = %s AND status != 'deleted'",
            (email,),
            fetch=True
        )
        return len(result) > 0
    except Exception as e:
        logger.error(f"检查邮箱失败: {e}")
        raise AuthException(code=500, message="数据库查询失败")


async def get_user_by_email(email: str) -> Optional[dict]:
    """通过邮箱获取用户信息"""
    try:
        result = execute_query(
            "SELECT * FROM employee_login_info WHERE email = %s AND status = 'active'",
            (email,),
            fetch=True
        )
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"获取用户失败: {e}")
        raise AuthException(code=500, message="数据库查询失败")


async def update_user_login(user_id: int, last_login_ip: str = None, increment_failed: bool = False):
    """更新用户登录信息"""
    try:
        if increment_failed:
            # 增加失败次数
            execute_query(
                """
                UPDATE employee_login_info
                SET failed_login_count = failed_login_count + 1,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (user_id,)
            )

            # 检查是否需要锁定账户
            user = await get_user_by_id(user_id)
            if user and user['failed_login_count'] + 1 >= MAX_FAILED_LOGIN_COUNT:
                lock_time = datetime.now() + timedelta(minutes=FAILED_LOGIN_LOCK_MINUTES)
                execute_query(
                    """
                    UPDATE employee_login_info
                    SET lock_until = %s, status = 'locked'
                    WHERE id = %s
                    """,
                    (lock_time, user_id)
                )
                logger.warning(f"账户已锁定: email={user['email']}")
        else:
            # 登录成功，重置失败次数，更新登录信息
            execute_query(
                """
                UPDATE employee_login_info
                SET last_login_at = NOW(),
                    last_login_ip = %s,
                    failed_login_count = 0,
                    lock_until = NULL,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (last_login_ip or 'NULL', user_id)
            )
    except Exception as e:
        logger.error(f"更新用户登录失败: {e}")
        raise AuthException(code=500, message="数据库更新失败")


async def get_user_by_id(user_id: int) -> Optional[dict]:
    """通过ID获取用户信息"""
    try:
        result = execute_query(
            "SELECT * FROM employee_login_info WHERE id = %s",
            (user_id,),
            fetch=True
        )
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"获取用户失败: {e}")
        raise AuthException(code=500, message="数据库查询失败")


async def save_verification_code(email: str, code: str) -> bool:
    """保存验证码"""
    try:
        execute_query(
            """
            UPDATE employee_login_info
            SET verification_code = %s,
                verification_code_sent_at = NOW(),
                verification_code_failed_count = 0
            WHERE email = %s AND status = 'active'
            """,
            (code, email)
        )
        return True
    except Exception as e:
        logger.error(f"保存验证码失败: {e}")
        raise AuthException(code=500, message="数据库更新失败")


async def verify_and_clear_code(email: str, code: str) -> Tuple[bool, str]:
    """验证验证码并清除"""
    try:
        result = execute_query(
            """
            SELECT verification_code,
                   verification_code_sent_at,
                   verification_code_failed_count,
                   email_verified_at
            FROM employee_login_info
            WHERE email = %s AND status = 'active'
            """,
            (email,),
            fetch=True
        )

        if not result:
            return False, "未找到用户"

        user = result[0]

        # 检查验证码是否过期
        if user['verification_code_sent_at']:
            sent_time = user['verification_code_sent_at']
            if isinstance(sent_time, str):
                sent_time = datetime.strptime(sent_time, '%Y-%m-%d %H:%M:%S')
            expiry_time = sent_time + timedelta(minutes=VERIFICATION_CODE_EXPIRE_MINUTES)
            if datetime.now() > expiry_time:
                return False, "验证码已过期"

        # 检查验证码是否匹配
        if user['verification_code'] != code:
            # 验证码错误，增加失败次数
            execute_query(
                """
                UPDATE employee_login_info
                SET verification_code_failed_count = verification_code_failed_count + 1
                WHERE email = %s
                """,
                (email,)
            )

            if user['verification_code_failed_count'] + 1 >= MAX_VERIFICATION_CODE_ATTEMPTS:
                return False, "验证码错误次数过多，请重新发送"

            return False, "验证码错误"

        # 验证成功
        execute_query(
            """
            UPDATE employee_login_info
            SET email_verified_at = NOW(),
                verification_code = NULL,
                verification_code_sent_at = NULL,
                verification_code_failed_count = 0
            WHERE email = %s
            """,
            (email,)
        )

        return True, "验证成功"

    except Exception as e:
        logger.error(f"验证验证码失败: {e}")
        return False, "验证失败，请稍后重试"


# API 端点

@auth_router.post(
    "/register",
    response_model=RegisterResponse,
    summary="用户注册",
)
async def register(request: RegisterRequest):
    """
    用户注册

    1. 验证邮箱格式
    2. 检查邮箱是否已存在
    3. 验证密码强度
    4. 哈希密码
    5. 存入数据库
    """
    try:
        # 检查邮箱是否已存在
        email_exists = await check_email_exists(request.email)
        if email_exists:
            return RegisterResponse(code=400, message="该邮箱已被注册")

        # 验证密码强度
        is_valid, password_msg = validate_password_strength(request.password)
        if not is_valid:
            return RegisterResponse(code=400, message=password_msg)

        # 哈希密码
        password_hash = hash_password(request.password)

        # 存入数据库
        execute_query(
            """
            INSERT INTO employee_login_info
            (email, password_hash, employee_id, name, department, phone, status, is_admin)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                request.email,
                password_hash,
                request.employee_id,
                request.name,
                request.department,
                request.phone,
                UserStatus.ACTIVE.value,
                0
            )
        )

        logger.info(f"用户注册成功: email={request.email}, name={request.name}")
        return RegisterResponse(code=200, message="注册成功，请登录")

    except Exception as e:
        logger.error(f"注册失败: {e}")
        raise AuthException(code=500, message="注册失败，请稍后重试")


@auth_router.post(
    "/login",
    response_model=LoginResponse,
    summary="用户登录(密码方式)",
)
async def login(
    request: LoginRequest = None
):
    """
    用户登录（密码方式）
    1. 查询用户信息
    2. 检查账户状态
    3. 验证密码
    4. 生成 JWT token
    5. 更新登录信息
    """
    try:
        # 查询用户
        user = await get_user_by_email(request.email)
        if not user:
            return LoginResponse(code=400, message="邮箱或密码错误", data=None)

        # 检查账户状态
        if user['status'] != 'active':
            if user['status'] == 'deleted':
                return LoginResponse(code=400, message="该账户已被删除", data=None)
            elif user['status'] == 'disabled':
                return LoginResponse(code=400, message="该账户已被禁用", data=None)
            elif user['status'] == 'locked':
                return LoginResponse(code=400, message="账户已锁定，请稍后重试", data=None)

        # 检查是否被锁定
        if user['lock_until'] and user['lock_until'] > datetime.now():
            return LoginResponse(
                code=400,
                message=f"账户已被锁定至 {user['lock_until']}",
                data=None
            )

        # 验证密码
        if not verify_password(request.password, user['password_hash']):
            # 密码错误，增加失败次数
            await update_user_login(user['id'], increment_failed=True)
            remaining = MAX_FAILED_LOGIN_COUNT - (user['failed_login_count'] + 1)
            if remaining <= 1:
                return LoginResponse(
                    code=400,
                    message="密码错误，账户即将被锁定",
                    data=None
                )
            else:
                return LoginResponse(
                    code=400,
                    message=f"密码错误，还剩 {remaining} 次机会",
                    data=None
                )

        # 登录成功
        # 获取客户端IP（需要从请求中获取）
        # 注意：FastAPI 中获取真实客户端IP需要额外配置
        # 这里暂时使用 'unknown'
        client_ip = 'unknown'

        await update_user_login(user['id'], last_login_ip=client_ip, increment_failed=False)

        # 生成 token
        access_token = create_access_token(data={"sub": user['email']})
        refresh_token = create_access_token(data={"sub": user['email'], "type": "refresh"})

        # 构建用户信息
        user_info = UserInfo(
            id=user['id'],
            email=user['email'],
            name=user['name'],
            department=user['department'],
            phone=user['phone'],
            avatar=user['avatar'],
            employee_id=user['employee_id'],
            is_admin=bool(user['is_admin']),
            last_login_at=user['last_login_at'],
            status=user['status']
        )

        login_data = LoginData(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_info
        )

        logger.info(f"用户登录成功: email={request.email}, id={user['id']}")
        return LoginResponse(code=200, message="登录成功", data=login_data)

    except AuthException as e:
        raise e
    except Exception as e:
        logger.error(f"登录失败: {e}")
        raise AuthException(code=500, message="登录失败，请稍后重试")


@auth_router.post("/login/code",
                  response_model=LoginResponse,
                  summary="用户登录(验证码方式)"
)
async def login_with_code(request: VerifyCodeLoginRequest):
    """
    验证码登录

    1. 查询用户信息
    2. 检查账户状态
    3. 验证验证码
    4. 检查密码（如果需要）
    5. 生成 JWT token
    6. 更新登录信息
    """
    try:
        # 查询用户
        user = await get_user_by_email(request.email)
        if not user:
            return LoginResponse(code=400, message="邮箱未注册", data=None)

        # 检查账户状态
        if user['status'] != 'active':
            return LoginResponse(code=400, message="账户状态异常", data=None)

        # 验证验证码
        is_valid, message = await verify_and_clear_code(request.email, request.code)
        if not is_valid:
            return LoginResponse(code=400, message=message, data=None)

        # 验证码登录不需要密码，直接登录成功
        await update_user_login(user['id'], increment_failed=False)

        # 生成 token(双Token认证机制)
        '''
        1. 用户登录                                         │
│     ↓                                               │
│     服务器返回:                                      │
│     - access_token (30分钟)                          │
│     - refresh_token (7天)                            │
│                                                     │
│  2. 用户访问 API                                     │
│     ↓                                               │
│     请求头携带: Authorization: Bearer <access_token>│
│     ↓                                               │
│     服务器验证 access_token                          │
│                                                     │
│  3. [30分钟后] Access Token 过期                     │
│     ↓                                               │
│     API 返回 401: "认证凭证已过期"                    │
│                                                     │
│  4. 前端检测到 401 错误                              │
│     ↓                                               │
│     自动调用刷新接口:                                 │
│     POST /api/auth/refresh                           │
│     Header: Authorization: Bearer <refresh_token>   │
│                                                     │
│  5. 服务器验证 refresh_token                         │
│     ↓                                               │
│     - 检查签名是否有效                                │
│     - 检查是否在黑名单中                              │
│     - 检查 type 是否为 "refresh"                     │
│     - 检查是否过期                                    │
│                                                     │
│  6. 验证成功                                         │
│     ↓                                               │
│     返回新的 access_token                            │
│     {                                               │
│       "access_token": "eyJhbG...",                  │
│       "token_type": "bearer",                        │
│       "expires_in": 1800                             │
│     }                                               │
│                                                     │
│  7. 前端保存新的 access_token                        │
│     ↓                                               │
│     用新 token 重新发起之前的请求                     │
│     （对用户透明，无感知）                            │
│                                                     │
│  8. [7天后] Refresh Token 也过期                     │
│     ↓                                               │
│     用户需要重新登录                     
        '''
        access_token = create_access_token(data={"sub": user['email']})
        refresh_token = create_access_token(data={"sub": user['email'], "type": "refresh"})

        # 构建用户信息
        user_info = UserInfo(
            id=user['id'],
            email=user['email'],
            name=user['name'],
            department=user['department'],
            phone=user['phone'],
            avatar=user['avatar'],
            employee_id=user['employee_id'],
            is_admin=bool(user['is_admin']),
            last_login_at=user['last_login_at'],
            status=user['status']
        )

        login_data = LoginData(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_info
        )

        logger.info(f"验证码登录成功: email={request.email}, id={user['id']}")
        return LoginResponse(code=200, message="登录成功", data=login_data)

    except AuthException as e:
        raise e
    except Exception as e:
        logger.error(f"验证码登录失败: {e}")
        raise AuthException(code=500, message="登录失败，请稍后重试")


@auth_router.post("/send-code",
                  summary="发送验证码(测试模式，直接返回验证码)",)
async def send_verification_code(request: SendCodeRequest):
    """
    发送验证码（测试模式，直接返回验证码）

    1. 检查邮箱是否存在
    2. 生成验证码
    3. 保存验证码
    4. 直接返回验证码（不再发送邮件）
    """
    try:
        # 检查邮箱是否已注册
        user = await get_user_by_email(request.email)
        if not user:
            return ErrorResponse(code=400, message="该邮箱未注册")

        # 检查发送频率
        if user['verification_code_sent_at']:
            sent_time = user['verification_code_sent_at']
            if isinstance(sent_time, str):
                sent_time = datetime.strptime(sent_time, '%Y-%m-%d %H:%M:%S')
            if datetime.now() - sent_time < timedelta(minutes=1):
                return ErrorResponse(code=400, message="验证码发送过于频繁，请1分钟后再试")

        # 检查失败次数
        if user['verification_code_failed_count'] >= MAX_VERIFICATION_CODE_ATTEMPTS:
            return ErrorResponse(code=400, message="验证码错误次数过多，请稍后重试")

        # 生成验证码
        code = generate_verification_code()

        # 保存验证码
        await save_verification_code(request.email, code)

        logger.info(f"验证码生成成功: email={request.email}, code={code}")
        # 直接返回验证码，供前端显示
        return {"code": 200, "message": "验证码生成成功", "data": {"verification_code": code}}

    except AuthException as e:
        raise e
    except Exception as e:
        logger.error(f"生成验证码失败: {e}")
        raise AuthException(code=500, message="生成验证码失败，请稍后重试")


@auth_router.post("/verify-code",
                  summary="仅验证验证码(用于前端验证)")
async def verify_code_only(request: VerifyCodeLoginRequest):
    """
    仅验证验证码（用于前端验证）

    不返回 token，只验证结果
    """
    try:
        is_valid, message = await verify_and_clear_code(request.email, request.code)
        if is_valid:
            return ErrorResponse(code=200, message=message)
        else:
            return ErrorResponse(code=400, message=message)

    except Exception as e:
        logger.error(f"验证码验证失败: {e}")
        raise AuthException(code=500, message="验证失败，请稍后重试")


@auth_router.get("/me",
                 summary="获取当前登录用户信息",
)
async def get_current_user(current_user: dict = Depends(verify_token)):
    """
    获取当前登录用户信息

    需要携带有效的 JWT token
    """
    try:
        email = current_user.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="无效的认证凭证")

        user = await get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        user_info = UserInfo(
            id=user['id'],
            email=user['email'],
            name=user['name'],
            department=user['department'],
            phone=user['phone'],
            avatar=user['avatar'],
            employee_id=user['employee_id'],
            is_admin=bool(user['is_admin']),
            last_login_at=user['last_login_at'],
            status=user['status']
        )

        return user_info

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise AuthException(code=500, message="获取用户信息失败")


@auth_router.post("/logout",
                  summary="用户登出"
)
async def logout(current_user: dict = Depends(verify_token), token: str = Depends(oauth2_scheme)):
    """
    用户登出

    1. 将当前 token 加入 Redis 黑名单
    2. 记录登出日志
    3. 前端应清除本地存储的 token
    """
    try:
        email = current_user.get("sub")

        # 解析 token 获取过期时间
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")

        if exp_timestamp:
            expires_at = datetime.fromtimestamp(exp_timestamp)
            # 将 token 加入黑名单
            success = await add_token_to_blacklist(token, email, expires_at)

            if success:
                logger.info(f"用户登出成功，token 已加入黑名单: email={email}")
            else:
                logger.warning(f"用户登出，但 token 加入黑名单失败: email={email}")
        else:
            logger.warning(f"用户登出，但 token 缺少过期时间: email={email}")

        return ErrorResponse(code=200, message="登出成功")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"登出失败: {e}")
        raise AuthException(code=500, message="登出失败")


@auth_router.post("/refresh",
                  summary="刷新访问token",
)
async def refresh_token(current_user: dict = Depends(verify_token)):
    """
    刷新访问 token

    需要携带有效的 refresh token
    """
    try:
        email = current_user.get("sub")
        token_type = current_user.get("type")

        if not email or token_type != "refresh":
            raise HTTPException(status_code=401, detail="无效的 refresh token")

        # 生成新的 access token
        access_token = create_access_token(data={"sub": email})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"刷新token失败: {e}")
        raise AuthException(code=500, message="刷新token失败")