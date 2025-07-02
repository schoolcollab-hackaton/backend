from fastapi import APIRouter, HTTPException, status, Depends, Response, Request
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging
from app.models.models import Utilisateur, UtilisateurSchema, UtilisateurRole
from app.utils import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ACCESS_TOKEN_EXPIRE_HOURS = 24

router = APIRouter(prefix="/auth", tags=["authentication"])


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
    access_token = create_access_token(user.id)

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
async def get_current_user_info(current_user: Utilisateur = Depends(get_current_user)):

    user_roles = await UtilisateurRole.filter(
        utilisateur=current_user, statut="active"
    ).all()
    roles = [role.role for role in user_roles]
    logger.debug(f"User roles: {roles}")

    user_schema = UtilisateurSchema(
        id=current_user.id,
        nom=current_user.nom,
        prenom=current_user.prenom,
        email=current_user.email,
        score=current_user.score,
        avatar=current_user.avatar,
        # discord=user.discord, 
        # linkedin=user.linkedin,
        profile_completed=current_user.profile_completed,
        filiere=current_user.filiere,
        niveau=current_user.niveau,
        roles=roles,
    )
    logger.debug("Successfully retrieved user info")
    return user_schema


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
