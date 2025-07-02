from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from app.models.models import (
    Utilisateur, 
    UtilisateurCompetence, 
    UtilisateurCentreInteret,
    UtilisateurParrainage,
    Competence,
    CentreInteret,
    FiliereEnum,
    NiveauEnum
)
from app.routers.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

class CompetenceInfo(BaseModel):
    id: int
    nom: str
    description: str
    niveau: str
    dateObtention: str

class CentreInteretInfo(BaseModel):
    id: int
    titre: str

class ParrainInfo(BaseModel):
    id: int
    nom: str
    prenom: str
    email: str

class DashboardResponse(BaseModel):
    competences: List[CompetenceInfo]
    centres_interet: List[CentreInteretInfo]
    parrain: Optional[ParrainInfo] = None
    filiere: Optional[FiliereEnum] = None
    niveau: Optional[NiveauEnum] = None
    score: int

@router.get("/", response_model=DashboardResponse)
async def get_user_dashboard(current_user: Utilisateur = Depends(get_current_user)):
    """Get user dashboard information including competences, interests, mentor, field, level, and score"""
    
    # Get user competences
    user_competences = await UtilisateurCompetence.filter(utilisateur=current_user).prefetch_related('competence')
    competences = [
        CompetenceInfo(
            id=uc.competence.id,
            nom=uc.competence.nom,
            description=uc.competence.description,
            niveau=uc.niveau,
            dateObtention=uc.dateObtention.isoformat()
        ) for uc in user_competences
    ]
    
    # Get user interests
    user_interests = await UtilisateurCentreInteret.filter(utilisateur=current_user).prefetch_related('centreInteret')
    centres_interet = [
        CentreInteretInfo(
            id=ui.centreInteret.id,
            titre=ui.centreInteret.titre
        ) for ui in user_interests
    ]
    
    # Get user mentor (parrain)
    parrain = None
    parrainage_relation = await UtilisateurParrainage.filter(
        utilisateur=current_user, 
        role="filleul"
    ).prefetch_related('parrainage__utilisateurs__utilisateur').first()
    
    if parrainage_relation:
        # Find the mentor (parrain) in the same parrainage
        parrain_relation = await UtilisateurParrainage.filter(
            parrainage=parrainage_relation.parrainage,
            role="parrain"
        ).prefetch_related('utilisateur').first()
        
        if parrain_relation:
            parrain_user = parrain_relation.utilisateur
            parrain = ParrainInfo(
                id=parrain_user.id,
                nom=parrain_user.nom,
                prenom=parrain_user.prenom,
                email=parrain_user.email
            )
    
    return DashboardResponse(
        competences=competences,
        centres_interet=centres_interet,
        parrain=parrain,
        filiere=current_user.filiere,
        niveau=current_user.niveau,
        score=current_user.score
    )