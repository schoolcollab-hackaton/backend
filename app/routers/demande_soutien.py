from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.models.models import DemandeSoutien, Utilisateur, Competence
from app.routers.auth import get_current_user

router = APIRouter(
    prefix="/demande-soutien",
    tags=["Demande de Soutien"]
)

# Schémas Pydantic
class DemandeSoutienBase(BaseModel):
    competence_id: int
    
class DemandeSoutienCreate(DemandeSoutienBase):
    pass

class DemandeSoutienUpdate(BaseModel):
    helper_id: Optional[int] = None
    statut: Optional[str] = None

class DemandeSoutienResponse(DemandeSoutienBase):
    id: int
    demandeur_id: int
    helper_id: Optional[int]
    statut: str
    dateDemande: datetime

    class Config:
        from_attributes = True

# Routes
@router.post("/", response_model=DemandeSoutienResponse)
async def create_demande_soutien(
    demande: DemandeSoutienCreate,
    current_user: Utilisateur = Depends(get_current_user)
):
    """Créer une nouvelle demande de soutien"""
    # Vérifier si la compétence existe
    competence = await Competence.get_or_none(id=demande.competence_id)
    if not competence:
        raise HTTPException(status_code=404, detail="Compétence non trouvée")

    # Créer la demande
    demande_obj = await DemandeSoutien.create(
        demandeur=current_user,
        competence=competence,
        statut="Pending"
    )
    return await DemandeSoutienResponse.from_tortoise_orm(demande_obj)

@router.get("/mes-demandes", response_model=List[DemandeSoutienResponse])
async def get_mes_demandes(current_user: Utilisateur = Depends(get_current_user)):
    """Récupérer toutes les demandes de l'utilisateur courant"""
    return await DemandeSoutienResponse.from_queryset(
        DemandeSoutien.filter(demandeur=current_user)
    )

@router.get("/en-attente", response_model=List[DemandeSoutienResponse])
async def get_demandes_en_attente(current_user: Utilisateur = Depends(get_current_user)):
    """Récupérer toutes les demandes en attente"""
    return await DemandeSoutienResponse.from_queryset(
        DemandeSoutien.filter(statut="Pending", helper__isnull=True)
    )

@router.get("/{demande_id}", response_model=DemandeSoutienResponse)
async def get_demande(
    demande_id: int,
    current_user: Utilisateur = Depends(get_current_user)
):
    """Récupérer une demande spécifique"""
    demande = await DemandeSoutien.get_or_none(id=demande_id)
    if not demande:
        raise HTTPException(status_code=404, detail="Demande non trouvée")
    return await DemandeSoutienResponse.from_tortoise_orm(demande)

@router.put("/{demande_id}", response_model=DemandeSoutienResponse)
async def update_demande(
    demande_id: int,
    demande_update: DemandeSoutienUpdate,
    current_user: Utilisateur = Depends(get_current_user)
):
    """Mettre à jour une demande de soutien"""
    demande = await DemandeSoutien.get_or_none(id=demande_id)
    if not demande:
        raise HTTPException(status_code=404, detail="Demande non trouvée")

    # Vérifier les permissions
    if demande.demandeur_id != current_user.id and demande.helper_id != current_user.id:
        raise HTTPException(status_code=403, detail="Non autorisé à modifier cette demande")

    # Mise à jour des champs
    update_data = demande_update.dict(exclude_unset=True)
    if "helper_id" in update_data:
        helper = await Utilisateur.get_or_none(id=update_data["helper_id"])
        if not helper:
            raise HTTPException(status_code=404, detail="Helper non trouvé")
        demande.helper = helper
    
    if "statut" in update_data:
        valid_statuts = ["Pending", "Approved", "Completed", "Cancelled"]
        if update_data["statut"] not in valid_statuts:
            raise HTTPException(status_code=400, detail="Statut invalide")
        demande.statut = update_data["statut"]

    await demande.save()
    return await DemandeSoutienResponse.from_tortoise_orm(demande)

@router.post("/{demande_id}/accepter", response_model=DemandeSoutienResponse)
async def accepter_demande(
    demande_id: int,
    current_user: Utilisateur = Depends(get_current_user)
):
    """Accepter une demande de soutien en tant que helper"""
    demande = await DemandeSoutien.get_or_none(id=demande_id)
    if not demande:
        raise HTTPException(status_code=404, detail="Demande non trouvée")

    if demande.helper_id is not None:
        raise HTTPException(status_code=400, detail="Cette demande a déjà un helper")

    if demande.statut != "Pending":
        raise HTTPException(status_code=400, detail="Cette demande n'est plus en attente")

    demande.helper = current_user
    demande.statut = "Approved"
    await demande.save()
    return await DemandeSoutienResponse.from_tortoise_orm(demande)

@router.delete("/{demande_id}")
async def delete_demande(
    demande_id: int,
    current_user: Utilisateur = Depends(get_current_user)
):
    """Supprimer une demande de soutien"""
    demande = await DemandeSoutien.get_or_none(id=demande_id)
    if not demande:
        raise HTTPException(status_code=404, detail="Demande non trouvée")

    if demande.demandeur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Non autorisé à supprimer cette demande")

    await demande.delete()
    return {"message": "Demande supprimée avec succès"} 