from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List
from app.models.models import Parrainage, UtilisateurParrainage, Utilisateur
from app.scoring.score_system import ajouter_points, ActionType
from datetime import datetime

router = APIRouter(prefix="/parrainages", tags=["parrainages"])


class ParrainageCreate(BaseModel):
    filleul_id: int
    message: Optional[str] = None


class ParrainageResponse(BaseModel):
    id: int
    statut: str
    dateDemande: datetime
    parrain_id: int
    filleul_id: int
    message: Optional[str] = None


# Fonction pour récupérer un utilisateur par ID
async def get_user_by_id(utilisateur_id: int):
    user = await Utilisateur.get_or_none(id=utilisateur_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utilisateur avec l'ID {utilisateur_id} non trouvé"
        )
    return user


# Route non authentifiée pour obtenir tous les parrainages
@router.get("/", response_model=List[ParrainageResponse])
async def lister_parrainages():
    """Récupérer tous les parrainages sans authentification"""
    parrainages = await Parrainage.all()

    result = []
    for parrainage in parrainages:
        # Chercher le parrain et le filleul
        parrain_relation = await UtilisateurParrainage.get_or_none(
            parrainage_id=parrainage.id,
            role="parrain"
        )

        filleul_relation = await UtilisateurParrainage.get_or_none(
            parrainage_id=parrainage.id,
            role="filleul"
        )

        if parrain_relation and filleul_relation:
            result.append(ParrainageResponse(
                id=parrainage.id,
                statut=parrainage.statut,
                dateDemande=parrainage.dateDemande,
                parrain_id=parrain_relation.utilisateur_id,
                filleul_id=filleul_relation.utilisateur_id,
                message=None  # Nous n'avons pas de champ message dans le modèle
            ))

    return result


# Route pour obtenir les parrainages de l'utilisateur identifié par son ID
@router.get("/mes-parrainages", response_model=List[ParrainageResponse])
async def mes_parrainages(utilisateur_id: int = Query(...)):
    """Récupérer les parrainages de l'utilisateur"""
    current_user = await get_user_by_id(utilisateur_id)

    relations = await UtilisateurParrainage.filter(utilisateur_id=current_user.id).prefetch_related("parrainage")

    result = []
    for relation in relations:
        parrainage = relation.parrainage

        if relation.role == "parrain":
            autre_relation = await UtilisateurParrainage.get_or_none(
                parrainage_id=parrainage.id,
                role="filleul"
            )
            parrain_id = current_user.id
            filleul_id = autre_relation.utilisateur_id if autre_relation else None
        else:
            autre_relation = await UtilisateurParrainage.get_or_none(
                parrainage_id=parrainage.id,
                role="parrain"
            )
            parrain_id = autre_relation.utilisateur_id if autre_relation else None
            filleul_id = current_user.id

        if filleul_id and parrain_id:
            result.append(ParrainageResponse(
                id=parrainage.id,
                statut=parrainage.statut,
                dateDemande=parrainage.dateDemande,
                parrain_id=parrain_id,
                filleul_id=filleul_id,
                message=None
            ))

    return result


@router.post("/", response_model=ParrainageResponse, status_code=status.HTTP_201_CREATED)
async def creer_parrainage(
        demande: ParrainageCreate,
        utilisateur_id: int = Query(...)
):
    """Créer une demande de parrainage"""
    current_user = await get_user_by_id(utilisateur_id)

    # Vérifier si le filleul existe
    filleul = await Utilisateur.get_or_none(id=demande.filleul_id)
    if not filleul:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utilisateur avec l'ID {demande.filleul_id} non trouvé"
        )

    # Vérifier qu'on ne se parraine pas soi-même
    if current_user.id == demande.filleul_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas vous parrainer vous-même"
        )

    # Créer l'objet Parrainage
    parrainage = await Parrainage.create(statut="Pending")

    # Associer le parrain
    await UtilisateurParrainage.create(
        utilisateur_id=current_user.id,
        parrainage_id=parrainage.id,
        role="parrain"
    )

    # Associer le filleul
    await UtilisateurParrainage.create(
        utilisateur_id=filleul.id,
        parrainage_id=parrainage.id,
        role="filleul"
    )

    # Ajouter des points pour la création du parrainage
    await ajouter_points(current_user.id, ActionType.PARRAINAGE_CREATION)

    return ParrainageResponse(
        id=parrainage.id,
        statut=parrainage.statut,
        dateDemande=parrainage.dateDemande,
        parrain_id=current_user.id,
        filleul_id=filleul.id,
        message=demande.message
    )


@router.put("/{parrainage_id}/accepter", status_code=status.HTTP_200_OK)
async def accepter_parrainage(
        parrainage_id: int,
        utilisateur_id: int = Query(...)
):
    """Accepter une demande de parrainage"""
    current_user = await get_user_by_id(utilisateur_id)

    # Vérifier si le parrainage existe
    parrainage = await Parrainage.get_or_none(id=parrainage_id)
    if not parrainage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parrainage avec l'ID {parrainage_id} non trouvé"
        )

    # Vérifier que l'utilisateur actuel est bien le filleul de ce parrainage
    relation = await UtilisateurParrainage.get_or_none(
        parrainage_id=parrainage_id,
        utilisateur_id=current_user.id,
        role="filleul"
    )

    if not relation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas autorisé à accepter ce parrainage"
        )

    # Vérifier que le parrainage est bien en attente
    if parrainage.statut != "Pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ce parrainage est déjà {parrainage.statut}"
        )

    # Mettre à jour le statut
    parrainage.statut = "Accepted"
    await parrainage.save()

    # Trouver l'ID du parrain
    parrain_relation = await UtilisateurParrainage.get_or_none(
        parrainage_id=parrainage_id,
        role="parrain"
    )

    # Ajouter des points pour l'acceptation du parrainage
    if parrain_relation:
        await ajouter_points(parrain_relation.utilisateur_id, ActionType.PARRAINAGE_ACCEPTATION)

    return {"message": "Parrainage accepté avec succès"}


@router.put("/{parrainage_id}/refuser", status_code=status.HTTP_200_OK)
async def refuser_parrainage(
        parrainage_id: int,
        utilisateur_id: int = Query(...)
):
    """Refuser une demande de parrainage"""
    current_user = await get_user_by_id(utilisateur_id)

    # Vérifier si le parrainage existe
    parrainage = await Parrainage.get_or_none(id=parrainage_id)
    if not parrainage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parrainage avec l'ID {parrainage_id} non trouvé"
        )

    # Vérifier que l'utilisateur actuel est bien le filleul de ce parrainage
    relation = await UtilisateurParrainage.get_or_none(
        parrainage_id=parrainage_id,
        utilisateur_id=current_user.id,
        role="filleul"
    )

    if not relation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas autorisé à refuser ce parrainage"
        )

    # Vérifier que le parrainage est bien en attente
    if parrainage.statut != "Pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ce parrainage est déjà {parrainage.statut}"
        )

    # Mettre à jour le statut
    parrainage.statut = "Refused"
    await parrainage.save()

    return {"message": "Parrainage refusé avec succès"}


@router.put("/{parrainage_id}/completer", status_code=status.HTTP_200_OK)
async def completer_parrainage(
        parrainage_id: int,
        utilisateur_id: int = Query(...)
):
    """Marquer un parrainage comme complété"""
    current_user = await get_user_by_id(utilisateur_id)

    # Vérifier si le parrainage existe
    parrainage = await Parrainage.get_or_none(id=parrainage_id)
    if not parrainage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parrainage avec l'ID {parrainage_id} non trouvé"
        )

    # Vérifier que le parrainage est bien accepté
    if parrainage.statut != "Accepted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ce parrainage doit être accepté pour être complété (statut actuel: {parrainage.statut})"
        )

    # Vérifier que l'utilisateur est impliqué dans ce parrainage
    relation = await UtilisateurParrainage.get_or_none(
        parrainage_id=parrainage_id,
        utilisateur_id=current_user.id
    )

    if not relation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas impliqué dans ce parrainage"
        )

    # Mettre à jour le statut
    parrainage.statut = "Completed"
    await parrainage.save()

    # Trouver le parrain et le filleul pour leur donner des points
    parrain_relation = await UtilisateurParrainage.get_or_none(
        parrainage_id=parrainage_id,
        role="parrain"
    )

    filleul_relation = await UtilisateurParrainage.get_or_none(
        parrainage_id=parrainage_id,
        role="filleul"
    )

    # Ajouter des points pour la complétion du parrainage
    if parrain_relation:
        await ajouter_points(parrain_relation.utilisateur_id, ActionType.PARRAINAGE_COMPLETION)

    if filleul_relation:
        await ajouter_points(filleul_relation.utilisateur_id, ActionType.PARRAINAGE_COMPLETION)

    return {"message": "Parrainage complété avec succès"}