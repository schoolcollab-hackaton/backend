from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from app.models.models import (
    Utilisateur,
    FiliereEnum,
    NiveauEnum,
    Competence,
    CentreInteret,
    UtilisateurCompetence,
    UtilisateurCentreInteret,
    UtilisateurRole,
    RoleEnum,
)
from app.utils import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileCompleteRequest(BaseModel):
    filiere: FiliereEnum
    niveau: NiveauEnum
    competences: Dict[str, str]
    centres_interet: List[str]
    is_mentor: Optional[bool] = False
    discord: Optional[str] = None
    linkedin: Optional[str] = None


@router.get("/competences")
async def get_competences():
    """Get all available competences from database"""
    competences = await Competence.all()
    return [{"nom": c.nom, "description": c.description} for c in competences]


@router.get("/centres-interet")
async def get_centres_interet():
    """Get all available centres d'intérêt from database"""
    centres = await CentreInteret.all()
    return [{"titre": c.titre} for c in centres]


@router.put("/complete")
async def complete_profile(
    profile_data: ProfileCompleteRequest,
    current_user: Utilisateur = Depends(get_current_user),
):
    """Complete user profile with filiere, niveau, competences and centres d'interet"""

    # Update user's filiere and niveau
    current_user.filiere = profile_data.filiere
    current_user.niveau = profile_data.niveau
    current_user.profile_completed = True
    if profile_data.discord:
        current_user.discord = profile_data.discord
    if profile_data.linkedin:
        current_user.linkedin = profile_data.linkedin
    await current_user.save()

    # Remove existing competences
    await UtilisateurCompetence.filter(utilisateur=current_user).delete()

    # Add new competences
    for competence_nom, competence_niveau in profile_data.competences.items():
        competence = await Competence.get_or_none(nom=competence_nom)
        if not competence:
            competence = await Competence.create(nom=competence_nom, description="")
        await UtilisateurCompetence.create(
            utilisateur=current_user,
            competence=competence,
            niveau=competence_niveau,
            statut="active",
        )

    # Remove existing centres d'interet
    await UtilisateurCentreInteret.filter(utilisateur=current_user).delete()

    # Add new centres d'interet
    for centre_titre in profile_data.centres_interet:
        centre = await CentreInteret.get_or_none(titre=centre_titre)
        if not centre:
            centre = await CentreInteret.create(titre=centre_titre)
        await UtilisateurCentreInteret.create(
            utilisateur=current_user, centreInteret=centre
        )

    # Handle mentor role assignment
    if profile_data.is_mentor:
        # Check if user already has mentor role
        existing_mentor_role = await UtilisateurRole.get_or_none(
            utilisateur=current_user, role=RoleEnum.MENTOR
        )
        if not existing_mentor_role:
            await UtilisateurRole.create(
                utilisateur=current_user, role=RoleEnum.MENTOR, statut="active"
            )

    return {
        "message": "Profile completed successfully",
        "filiere": current_user.filiere,
        "niveau": current_user.niveau,
        "competences_count": len(profile_data.competences),
        "centres_interet_count": len(profile_data.centres_interet),
        "is_mentor": profile_data.is_mentor,
    }
