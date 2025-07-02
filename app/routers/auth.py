from fastapi import APIRouter, HTTPException, status, Depends, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging
from app.models.models import Utilisateur, UtilisateurSchema, UtilisateurRole
from app.utils import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ACCESS_TOKEN_EXPIRE_HOURS = 24

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


# Pydantic models for requests
class UserRegister(BaseModel):
    nom: str
    prenom: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UtilisateurSchema


# Authentication dependency
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    user_id = verify_token(token)
    user = await Utilisateur.get_or_none(id=int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


@router.post("/register", response_model=Token)
async def register(user_data: UserRegister):
    """Register a new user"""
    # Check if user already exists
    existing_user = await Utilisateur.get_or_none(email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Hash password
    hashed_password = get_password_hash(user_data.password)

    # Create new user
    user = await Utilisateur.create(
        nom=user_data.nom,
        prenom=user_data.prenom,
        email=user_data.email,
        password=hashed_password,
        score=0,
    )

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    # Convert to schema
    user_schema = UtilisateurSchema(
        id=user.id,
        nom=user.nom,
        prenom=user.prenom,
        email=user.email,
        score=user.score,
        avatar=user.avatar,
    )

    return Token(access_token=access_token, token_type="bearer", user=user_schema)


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, response: Response):
    """Login user"""
    # Get user by email
    user = await Utilisateur.get_or_none(email=user_credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(user_credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    # Set httpOnly cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_HOURS * 60 * 60,  # 24 hours in seconds
        httponly=True,
        secure=False,  # HTTPS only in production
        samesite="lax",
    )

    # Convert to schema
    user_schema = UtilisateurSchema(
        id=user.id,
        nom=user.nom,
        prenom=user.prenom,
        email=user.email,
        score=user.score,
        avatar=user.avatar,
        filiere=user.filiere,
        niveau=user.niveau,
        profile_completed=user.profile_completed,
    )

    return Token(access_token=access_token, token_type="bearer", user=user_schema)


@router.get("/me", response_model=UtilisateurSchema)
async def get_current_user_info(request: Request):
    """Get current user information from httpOnly cookie"""
    try:
        logger.debug("Accessing /auth/me endpoint")
        logger.debug(f"Request cookies: {request.cookies}")

        cookie_token = request.cookies.get("access_token")
        if not cookie_token:
            logger.error("No access_token cookie found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        logger.debug("Verifying token")
        try:
            user_id = verify_token(cookie_token)
            logger.debug(f"Token verified, user_id: {user_id}")
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
            )

        logger.debug(f"Fetching user with id: {user_id}")
        user = await Utilisateur.get_or_none(id=int(user_id))
        if user is None:
            logger.error(f"No user found with id: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        logger.debug("Fetching user roles")
        user_roles = await UtilisateurRole.filter(
            utilisateur=user, statut="active"
        ).all()
        roles = [role.role for role in user_roles]
        logger.debug(f"User roles: {roles}")

        user_schema = UtilisateurSchema(
            id=user.id,
            nom=user.nom,
            prenom=user.prenom,
            email=user.email,
            score=user.score,
            avatar=user.avatar,
            # discord=user.discord,
            # linkedin=user.linkedin,
            profile_completed=user.profile_completed,
            filiere=user.filiere,
            niveau=user.niveau,
            roles=roles,
        )
        logger.debug("Successfully retrieved user info")
        return user_schema

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /auth/me endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.put("/me", response_model=UtilisateurSchema)
async def update_current_user(
    user_update: UserRegister, current_user: Utilisateur = Depends(get_current_user)
):
    """Update current user information"""
    # Update user fields
    current_user.nom = user_update.nom
    current_user.prenom = user_update.prenom

    # Update password if provided
    if user_update.password:
        current_user.password = get_password_hash(user_update.password)

    await current_user.save()

    return UtilisateurSchema(
        id=current_user.id,
        nom=current_user.nom,
        prenom=current_user.prenom,
        email=current_user.email,
        score=current_user.score,
        avatar=current_user.avatar,
    )


@router.post("/logout")
async def logout(response: Response):
    """Logout user by clearing the httpOnly cookie"""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
    )
    return {"message": "Successfully logged out"}
