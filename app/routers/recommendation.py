from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.models.models import (
    Utilisateur, 
    FiliereEnum, 
    NiveauEnum, 
    RoleEnum
)
from app.utils import verify_token
from app.ai.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
security = HTTPBearer()

# Response models
class SkillDetail(BaseModel):
    skill: str
    their_level: Optional[int] = None
    your_level: Optional[int] = None
    benefit: str

class SwapDetails(BaseModel):
    skills_they_offer: List[SkillDetail]
    skills_you_offer: List[SkillDetail]
    mutual_benefits: List[str]
    skill_gaps_filled: int
    complementary_skills: int

class SkillSwapRecommendation(BaseModel):
    id: int
    nom: str
    prenom: str
    score: int
    filiere: Optional[FiliereEnum] = None
    niveau: Optional[NiveauEnum] = None
    roles: List[RoleEnum]
    interests: List[str]
    competences: List[Dict[str, Any]]
    swap_score: float
    swap_details: SwapDetails
    recommendation_type: str

class StudyBuddyRecommendation(BaseModel):
    id: int
    nom: str
    prenom: str
    score: int
    filiere: Optional[FiliereEnum] = None
    niveau: Optional[NiveauEnum] = None
    roles: List[RoleEnum]
    interests: List[str]
    competences: List[Dict[str, Any]]
    match_type: str
    similarity_score: float

class MentorRecommendation(BaseModel):
    id: int
    nom: str
    prenom: str
    score: int
    filiere: Optional[FiliereEnum] = None
    niveau: Optional[NiveauEnum] = None
    roles: List[RoleEnum]
    interests: List[str]
    competences: List[Dict[str, Any]]
    match_score: float
    match_type: str

class GroupRecommendation(BaseModel):
    id: int
    nom: str
    description: str
    interest: str
    match_score: float

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user_id = verify_token(token)
    user = await Utilisateur.get_or_none(id=int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user

@router.get("/skill-swap", response_model=List[SkillSwapRecommendation])
async def get_skill_swap_recommendations(
    limit: int = Query(default=10, ge=1, le=20, description="Maximum number of recommendations"),
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Get AI-powered skill swap recommendations.
    Finds users who have skills you lack or need improvement in, and vice versa.
    """
    try:
        recommendation_service = RecommendationService()
        recommendations = await recommendation_service.skill_swap(current_user.id, limit)
        
        # Convert to response model
        response_recommendations = []
        for rec in recommendations:
            # Convert swap_details to proper format
            swap_details = rec.get('swap_details', {})
            
            # Convert skills_they_offer
            skills_they_offer = []
            for skill in swap_details.get('skills_they_offer', []):
                skills_they_offer.append(SkillDetail(
                    skill=skill.get('skill', ''),
                    their_level=skill.get('their_level'),
                    your_level=skill.get('your_level'),
                    benefit=skill.get('benefit', '')
                ))
            
            # Convert skills_you_offer
            skills_you_offer = []
            for skill in swap_details.get('skills_you_offer', []):
                skills_you_offer.append(SkillDetail(
                    skill=skill.get('skill', ''),
                    their_level=skill.get('their_level'),
                    your_level=skill.get('your_level'),
                    benefit=skill.get('benefit', '')
                ))
            
            formatted_swap_details = SwapDetails(
                skills_they_offer=skills_they_offer,
                skills_you_offer=skills_you_offer,
                mutual_benefits=swap_details.get('mutual_benefits', []),
                skill_gaps_filled=swap_details.get('skill_gaps_filled', 0),
                complementary_skills=swap_details.get('complementary_skills', 0)
            )
            
            response_recommendations.append(SkillSwapRecommendation(
                id=rec['id'],
                nom=rec['nom'],
                prenom=rec['prenom'],
                score=rec['score'],
                filiere=rec.get('filiere'),
                niveau=rec.get('niveau'),
                roles=rec.get('roles', []),
                interests=rec.get('interests', []),
                competences=rec.get('competences', []),
                swap_score=rec['swap_score'],
                swap_details=formatted_swap_details,
                recommendation_type=rec['recommendation_type']
            ))
        
        return response_recommendations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating skill swap recommendations: {str(e)}"
        )

@router.get("/study-buddies", response_model=List[StudyBuddyRecommendation])
async def get_study_buddy_recommendations(
    limit: int = Query(default=5, ge=1, le=20, description="Maximum number of recommendations"),
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Get study buddy recommendations based on similar interests and academic level.
    """
    try:
        recommendation_service = RecommendationService()
        recommendations = await recommendation_service.find_study_buddies(current_user.id, limit)
        
        response_recommendations = []
        for rec in recommendations:
            response_recommendations.append(StudyBuddyRecommendation(
                id=rec['id'],
                nom=rec['nom'],
                prenom=rec['prenom'],
                score=rec['score'],
                filiere=rec.get('filiere'),
                niveau=rec.get('niveau'),
                roles=rec.get('roles', []),
                interests=rec.get('interests', []),
                competences=rec.get('competences', []),
                match_type=rec['match_type'],
                similarity_score=rec['similarity_score']
            ))
        
        return response_recommendations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating study buddy recommendations: {str(e)}"
        )

@router.get("/mentors", response_model=List[MentorRecommendation])
async def get_mentor_recommendations(
    limit: int = Query(default=5, ge=1, le=20, description="Maximum number of recommendations"),
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Get mentor recommendations based on competency gaps and academic progression.
    """
    try:
        recommendation_service = RecommendationService()
        recommendations = await recommendation_service.find_mentors(current_user.id, limit)
        
        response_recommendations = []
        for rec in recommendations:
            response_recommendations.append(MentorRecommendation(
                id=rec['id'],
                nom=rec['nom'],
                prenom=rec['prenom'],
                score=rec['score'],
                filiere=rec.get('filiere'),
                niveau=rec.get('niveau'),
                roles=rec.get('roles', []),
                interests=rec.get('interests', []),
                competences=rec.get('competences', []),
                match_score=rec['match_score'],
                match_type=rec['match_type']
            ))
        
        return response_recommendations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating mentor recommendations: {str(e)}"
        )

@router.get("/interdisciplinary", response_model=List[StudyBuddyRecommendation])
async def get_interdisciplinary_recommendations(
    limit: int = Query(default=5, ge=1, le=20, description="Maximum number of recommendations"),
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Get interdisciplinary collaboration recommendations from different academic programs.
    """
    try:
        recommendation_service = RecommendationService()
        recommendations = await recommendation_service.find_interdisciplinary_collaborators(current_user.id, limit)
        
        response_recommendations = []
        for rec in recommendations:
            response_recommendations.append(StudyBuddyRecommendation(
                id=rec['id'],
                nom=rec['nom'],
                prenom=rec['prenom'],
                score=rec['score'],
                filiere=rec.get('filiere'),
                niveau=rec.get('niveau'),
                roles=rec.get('roles', []),
                interests=rec.get('interests', []),
                competences=rec.get('competences', []),
                match_type=rec['match_type'],
                similarity_score=rec['collaboration_score']
            ))
        
        return response_recommendations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating interdisciplinary recommendations: {str(e)}"
        )

@router.get("/groups", response_model=List[GroupRecommendation])
async def get_group_recommendations(
    limit: int = Query(default=5, ge=1, le=20, description="Maximum number of recommendations"),
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Get group recommendations based on user interests.
    """
    try:
        recommendation_service = RecommendationService()
        recommendations = await recommendation_service.get_group_recommendations(current_user.id, limit)
        
        response_recommendations = []
        for rec in recommendations:
            response_recommendations.append(GroupRecommendation(
                id=rec['id'],
                nom=rec['nom'],
                description=rec['description'],
                interest=rec['interest'],
                match_score=rec['match_score']
            ))
        
        return response_recommendations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating group recommendations: {str(e)}"
        )

@router.get("/semantic", response_model=List[StudyBuddyRecommendation])
async def get_semantic_recommendations(
    limit: int = Query(default=5, ge=1, le=20, description="Maximum number of recommendations"),
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Get semantic similarity recommendations using AI profile matching.
    """
    try:
        recommendation_service = RecommendationService()
        recommendations = await recommendation_service.get_semantic_matches(current_user.id, limit)
        
        response_recommendations = []
        for rec in recommendations:
            response_recommendations.append(StudyBuddyRecommendation(
                id=rec['id'],
                nom=rec['nom'],
                prenom=rec['prenom'],
                score=rec['score'],
                filiere=rec.get('filiere'),
                niveau=rec.get('niveau'),
                roles=rec.get('roles', []),
                interests=rec.get('interests', []),
                competences=rec.get('competences', []),
                match_type=rec['match_type'],
                similarity_score=rec['semantic_score']
            ))
        
        return response_recommendations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating semantic recommendations: {str(e)}"
        )