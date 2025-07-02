import os
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, status
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    logger.debug(f"Creating access token with data: {data}")
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    logger.debug(f"Token payload: {to_encode}")

    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.debug("Token created successfully")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating token: {str(e)}")
        raise


def verify_token(token: str):
    logger.debug("Verifying token")
    try:
        logger.debug(
            f"Token being verified: {token[:10]}..."
        )  # Only log first 10 chars for security
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug(f"Token payload decoded: {payload}")
        user_id = payload.get("sub")
        if user_id is None:
            logger.error("Token payload missing 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing user ID"
            )
        return user_id
    except JWTError as e:
        logger.error(f"JWT verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification error: {str(e)}",
        )


def get_allowed_origins():
    origins = [
        "http://localhost:3000",
        "http://localhost:5000",
        "http://localhost:5173",
    ]

    host = os.getenv("HOST", "127.0.0.1")
    print(f"Detected host: {host}")
    if host != "127.0.0.1":
        origins.extend(
            [
                f"http://{host}:3000",
                f"http://{host}:5000",
                f"http://{host}:5173",
            ]
        )

    return origins
