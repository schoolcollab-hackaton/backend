from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from app.models.models import (
    Utilisateur,
    UtilisateurSchema,
    UtilisateurRole,
    RoleEnum,
    FiliereEnum,
    NiveauEnum,
    CentreInteret,
    Competence,
    UtilisateurCentreInteret,
    UtilisateurCompetence,
)
from app.utils import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
)

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


class CompleteProfileRequest(BaseModel):
    filiere: FiliereEnum
    niveau: NiveauEnum
    competences: dict[str, str]  # competence name -> level
    centresInteret: List[str]


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
        isProfileComplete=False,
    )

    # Create default student role
    await UtilisateurRole.create(utilisateur=user, role=RoleEnum.STUDENT)

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
        filiere=user.filiere,
        niveau=user.niveau,
        isProfileComplete=user.isProfileComplete,
        roles=[RoleEnum.STUDENT],
    )

    return Token(access_token=access_token, token_type="bearer", user=user_schema)


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
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

    # Get user roles
    user_roles = await UtilisateurRole.filter(utilisateur=user, statut="active")
    roles = [ur.role for ur in user_roles]

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
        filiere=user.filiere,
        niveau=user.niveau,
        isProfileComplete=user.isProfileComplete,
        roles=roles,
    )

    return Token(access_token=access_token, token_type="bearer", user=user_schema)


@router.get("/me", response_model=UtilisateurSchema)
async def get_current_user_info(current_user: Utilisateur = Depends(get_current_user)):
    """Get current user information"""
    # Get user roles
    user_roles = await UtilisateurRole.filter(utilisateur=current_user, statut="active")
    roles = [ur.role for ur in user_roles]

    return UtilisateurSchema(
        id=current_user.id,
        nom=current_user.nom,
        prenom=current_user.prenom,
        email=current_user.email,
        score=current_user.score,
        avatar=current_user.avatar,
        filiere=current_user.filiere,
        niveau=current_user.niveau,
        isProfileComplete=current_user.isProfileComplete,
        roles=roles,
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

    # Get user roles
    user_roles = await UtilisateurRole.filter(utilisateur=current_user, statut="active")
    roles = [ur.role for ur in user_roles]

    return UtilisateurSchema(
        id=current_user.id,
        nom=current_user.nom,
        prenom=current_user.prenom,
        email=current_user.email,
        score=current_user.score,
        avatar=current_user.avatar,
        filiere=current_user.filiere,
        niveau=current_user.niveau,
        isProfileComplete=current_user.isProfileComplete,
        roles=roles,
    )


@router.post("/complete-profile", response_model=UtilisateurSchema)
async def complete_profile(
    profile_data: CompleteProfileRequest,
    current_user: Utilisateur = Depends(get_current_user),
):
    """Complete user profile with filiere, niveau, competences, and interests"""
    try:
        # Update user's basic profile info
        current_user.filiere = profile_data.filiere
        current_user.niveau = profile_data.niveau
        current_user.isProfileComplete = True
        await current_user.save()

        # Handle competences
        for comp_name, level in profile_data.competences.items():
            # Get or create competence
            competence, _ = await Competence.get_or_create(
                nom=comp_name, defaults={"description": f"Compétence en {comp_name}"}
            )

            # Create user-competence relation
            await UtilisateurCompetence.get_or_create(
                utilisateur=current_user,
                competence=competence,
                defaults={"niveau": level, "statut": "active"},
            )

        # Handle centres d'intérêt
        for centre_name in profile_data.centresInteret:
            # Get or create centre d'intérêt
            centre, _ = await CentreInteret.get_or_create(titre=centre_name)

            # Create user-centre relation
            await UtilisateurCentreInteret.get_or_create(
                utilisateur=current_user, centreInteret=centre
            )

        # Get user roles for response
        user_roles = await UtilisateurRole.filter(
            utilisateur=current_user, statut="active"
        )
        roles = [ur.role for ur in user_roles]

        return UtilisateurSchema(
            id=current_user.id,
            nom=current_user.nom,
            prenom=current_user.prenom,
            email=current_user.email,
            score=current_user.score,
            avatar=current_user.avatar,
            filiere=current_user.filiere,
            niveau=current_user.niveau,
            isProfileComplete=current_user.isProfileComplete,
            roles=roles,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error completing profile: {str(e)}",
        )
