from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.models.models import UtilisateurMentor, Utilisateur, UtilisateurSchema
from app.utils import get_current_user

router = APIRouter(prefix="/mentorships", tags=["mentorships"])

# Pydantic models for responses
class MentorshipResponse(BaseModel):
    id: int
    utilisateur_id: int
    mentor_id: int
    date_added: str
    status: str
    utilisateur: Optional[UtilisateurSchema] = None
    mentor: Optional[UtilisateurSchema] = None
    
    class Config:
        from_attributes = True

@router.get("/mine", response_model=List[MentorshipResponse])
async def get_my_mentorships(
    current_user: Utilisateur = Depends(get_current_user)
):
    """Get all mentorship relationships for current user (both as mentor and mentee)"""
    # Get relationships where current user is a mentee
    as_mentee = await UtilisateurMentor.filter(utilisateur_id=current_user.id).prefetch_related('mentor').all()
    
    # Get relationships where current user is a mentor
    as_mentor = await UtilisateurMentor.filter(mentor_id=current_user.id).prefetch_related('utilisateur').all()
    
    all_relationships = []
    
    # Add mentee relationships
    for relationship in as_mentee:
        mentor = await Utilisateur.get(id=relationship.mentor_id)
        all_relationships.append(MentorshipResponse(
            id=relationship.id,
            utilisateur_id=relationship.utilisateur_id,
            mentor_id=relationship.mentor_id,
            date_added=str(relationship.date_added),
            status=relationship.status,
            mentor=UtilisateurSchema(
                id=mentor.id,
                nom=mentor.nom,
                prenom=mentor.prenom,
                email=mentor.email,
                score=mentor.score,
                avatar=mentor.avatar,
                discord=mentor.discord,
                linkedin=mentor.linkedin,
                filiere=mentor.filiere,
                niveau=mentor.niveau,
                profile_completed=mentor.profile_completed
            )
        ))
    
    # Add mentor relationships
    for relationship in as_mentor:
        mentee = await Utilisateur.get(id=relationship.utilisateur_id)
        all_relationships.append(MentorshipResponse(
            id=relationship.id,
            utilisateur_id=relationship.utilisateur_id,
            mentor_id=relationship.mentor_id,
            date_added=str(relationship.date_added),
            status=relationship.status,
            utilisateur=UtilisateurSchema(
                id=mentee.id,
                nom=mentee.nom,
                prenom=mentee.prenom,
                email=mentee.email,
                score=mentee.score,
                avatar=mentee.avatar,
                discord=mentee.discord,
                linkedin=mentee.linkedin,
                filiere=mentee.filiere,
                niveau=mentee.niveau,
                profile_completed=mentee.profile_completed
            )
        ))
    
    return all_relationships

@router.get("/mentees", response_model=List[MentorshipResponse])
async def get_my_mentees(
    current_user: Utilisateur = Depends(get_current_user)
):
    """Get all mentees of current user (where current user is the mentor)"""
    relationships = await UtilisateurMentor.filter(mentor_id=current_user.id).all()
    
    result = []
    for relationship in relationships:
        mentee = await Utilisateur.get(id=relationship.utilisateur_id)
        result.append(MentorshipResponse(
            id=relationship.id,
            utilisateur_id=relationship.utilisateur_id,
            mentor_id=relationship.mentor_id,
            date_added=str(relationship.date_added),
            status=relationship.status,
            utilisateur=UtilisateurSchema(
                id=mentee.id,
                nom=mentee.nom,
                prenom=mentee.prenom,
                email=mentee.email,
                score=mentee.score,
                avatar=mentee.avatar,
                discord=mentee.discord,
                linkedin=mentee.linkedin,
                filiere=mentee.filiere,
                niveau=mentee.niveau,
                profile_completed=mentee.profile_completed
            )
        ))
    
    return result

@router.get("/mentors", response_model=List[MentorshipResponse])
async def get_my_mentors(
    current_user: Utilisateur = Depends(get_current_user)
):
    """Get all mentors of current user (where current user is the mentee)"""
    relationships = await UtilisateurMentor.filter(utilisateur_id=current_user.id).all()
    
    result = []
    for relationship in relationships:
        mentor = await Utilisateur.get(id=relationship.mentor_id)
        result.append(MentorshipResponse(
            id=relationship.id,
            utilisateur_id=relationship.utilisateur_id,
            mentor_id=relationship.mentor_id,
            date_added=str(relationship.date_added),
            status=relationship.status,
            mentor=UtilisateurSchema(
                id=mentor.id,
                nom=mentor.nom,
                prenom=mentor.prenom,
                email=mentor.email,
                score=mentor.score,
                avatar=mentor.avatar,
                discord=mentor.discord,
                linkedin=mentor.linkedin,
                filiere=mentor.filiere,
                niveau=mentor.niveau,
                profile_completed=mentor.profile_completed
            )
        ))
    
    return result

@router.delete("/{mentorship_id}")
async def remove_mentorship(
    mentorship_id: int,
    current_user: Utilisateur = Depends(get_current_user)
):
    """Remove a mentorship relationship"""
    relationship = await UtilisateurMentor.get_or_none(id=mentorship_id)
    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentorship relationship not found"
        )
    
    # Check if current user is involved in this relationship
    if relationship.utilisateur_id != current_user.id and relationship.mentor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only remove your own mentorship relationships"
        )
    
    await relationship.delete()
    return {"message": "Mentorship relationship removed successfully"}

@router.put("/{mentorship_id}/block")
async def block_mentorship(
    mentorship_id: int,
    current_user: Utilisateur = Depends(get_current_user)
):
    """Block a mentorship relationship"""
    relationship = await UtilisateurMentor.get_or_none(id=mentorship_id)
    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentorship relationship not found"
        )
    
    # Check if current user is involved in this relationship
    if relationship.utilisateur_id != current_user.id and relationship.mentor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only block your own mentorship relationships"
        )
    
    relationship.status = "blocked"
    await relationship.save()
    
    return {"message": "Mentorship relationship blocked successfully"}

@router.put("/{mentorship_id}/unblock")
async def unblock_mentorship(
    mentorship_id: int,
    current_user: Utilisateur = Depends(get_current_user)
):
    """Unblock a mentorship relationship"""
    relationship = await UtilisateurMentor.get_or_none(id=mentorship_id)
    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentorship relationship not found"
        )
    
    # Check if current user is involved in this relationship
    if relationship.utilisateur_id != current_user.id and relationship.mentor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only unblock your own mentorship relationships"
        )
    
    relationship.status = "active"
    await relationship.save()
    
    return {"message": "Mentorship relationship unblocked successfully"}