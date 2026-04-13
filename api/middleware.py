# middleware.py - JWT 认证中间件
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status,Request
from fastapi.security import OAuth2,OAuth2PasswordRequestForm
from fastapi.security.utils import get_authorization_scheme_param
from starlette.datastructures import FormData
from api.redis_client import get_redis_client

# 日志
logger = logging.getLogger(__name__)

# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


# 自定义 OAuth2PasswordBearer（支持 email 字段）
class EmailPasswordBearer(OAuth2):
    """自定义 OAuth2 方案，使用 email 代替 username"""

    def __init__(
            self,
            tokenUrl: str,
            scheme_name: str = None,
            scopes: dict = None,
            auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = {
            "password": {
                "tokenUrl": tokenUrl,
                "scopes": scopes,
            }
        }
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)
        self.tokenUrl = tokenUrl

    async def __call__(self, request: Request) -> Optional[str]:
        authorization = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return param

# OAuth2 密码方案（JWT使用 bearer token）
# OAuth2 密码方案（JWT使用 bearer token）
oauth2_scheme = EmailPasswordBearer(tokenUrl="api/auth/login", auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT access token

    Args:
        data: 要编码到 token 中的数据（通常是 {"sub": email}）
        expires_delta: token 过期时间，默认使用配置值

    Returns:
        str: JWT token 字符串
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = data.copy()
    # 向 Payload 中添加 JWT 标准声明（Claims）
    to_encode.update({
        "exp": expire,  # 添加过期时间
        "iat": datetime.utcnow() # 记录Token生成时间
    })
    # 使用指定的密钥和算法对 Payload 进行签名和编码
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def check_token_blacklist(token: str) -> bool:
    """
    检查 token 是否在黑名单中

    Args:
        token: JWT token

    Returns:
        bool: True 表示在黑名单中，False 表示不在
    """
    try:
        redis_client = get_redis_client()
        if redis_client is None:
            # Redis 不可用时，跳过黑名单检查
            logger.warning("Redis 不可用，跳过黑名单检查")
            return False

        # 检查 token 是否在黑名单中
        blacklisted = redis_client.exists(f"blacklist:{token}")
        return blacklisted > 0
    except Exception as e:
        logger.error(f"检查 token 黑名单失败: {e}")
        # 发生错误时不阻止用户访问，但记录日志
        return False


async def add_token_to_blacklist(token: str, email: str, expires_at: datetime) -> bool:
    """
    将 token 加入黑名单

    Args:
        token: JWT token
        email: 用户邮箱
        expires_at: token 过期时间

    Returns:
        bool: 是否成功加入黑名单
    """
    try:
        redis_client = get_redis_client()
        if redis_client is None:
            logger.warning("Redis 不可用，无法将 token 加入黑名单")
            return False

        # 计算 TTL（剩余有效时间）
        ttl = int((expires_at - datetime.utcnow()).total_seconds())

        if ttl > 0:
            # 将 token 加入黑名单，设置过期时间
            key = f"blacklist:{token}"
            redis_client.setex(key, ttl, email)
            logger.info(f"Token 已加入黑名单: email={email}, ttl={ttl}s")
            return True
        else:
            logger.warning(f"Token 已过期，无需加入黑名单: email={email}")
            return False

    except Exception as e:
        logger.error(f"添加 token 到黑名单失败: {e}")
        return False


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Optional[Dict]:
    """
    获取当前用户信息（从 token 中解析）

    Args:
        token: JWT token

    Returns:
        dict: 包含用户信息的字典，如 {"sub": "email", "type": "access"}

    Raises:
        HTTPException: token 无效或过期
    """
    try:
        # 首先检查 token 是否在黑名单中
        if await check_token_blacklist(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token 已失效，请重新登录"
            )

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭证"
            )

        # 检查 token 是否过期
        exp = payload.get("exp")
        if exp is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭证"
            )

        if datetime.utcnow() > datetime.fromtimestamp(exp):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证凭证已过期，请重新登录"
            )

        return {
            "sub": email,
            "type": payload.get("type", "access")
        }

    except JWTError as e:
        logger.warning(f"JWT 解析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证"
        )


async def verify_token(token: str = Depends(oauth2_scheme)) -> Dict:
    """
    验证 token 有效性（简化版本，不解析用户信息）

    主要用于不需要用户信息的路由保护

    Args:
        token: JWT token

    Returns:
        dict: 包含 sub 的字典

    Raises:
        HTTPException: token 无效或过期
    """
    try:
        # 首先检查 token 是否在黑名单中
        if await check_token_blacklist(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token 已失效，请重新登录"
            )

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭证"
            )

        # 检查 token 是否过期
        exp = payload.get("exp")
        if exp is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭证"
            )

        if datetime.utcnow() > datetime.fromtimestamp(exp):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证凭证已过期，请重新登录"
            )

        return {"sub": email}

    except JWTError as e:
        logger.warning(f"JWT 解析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证"
        )


class OptionalAuth:
    """
    可选认证依赖（可选登录）
    用于某些既可以登录也可以不登录的端点
    """
    async def __call__(token: str = Depends(oauth2_scheme)):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return {"sub": payload.get("sub"), "type": payload.get("type", "access")}
        except JWTError:
            return None
        except Exception:
            return None


# 可选认证依赖实例
optional_auth = OptionalAuth()


def get_optional_user(user: Optional[dict] = Depends(optional_auth)) -> Optional[dict]:
    """
    获取可选用户信息（可能为 None）
    """
    return user