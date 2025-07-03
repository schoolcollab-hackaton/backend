from fastapi import APIRouter, Depends, HTTPException, status
from app.models.models import Utilisateur, Groupe, UtilisateurGroupe
from app.models.models import CentreInteret
from app.utils import get_current_user
from pydantic import BaseModel

class ChangementRole(BaseModel):
    utilisateur_id: int
    nouveau_role: str  # "member", "moderator", "administrator"

class GroupeCreate(BaseModel):
    nom: str
    description: str
    centre_interet_id: int

router = APIRouter(prefix="/groupes", tags=["groupes"])

@router.post("/creer")
async def creer_groupe(
        groupe_data: GroupeCreate,
        current_user: Utilisateur = Depends(get_current_user)
):
    centre = await CentreInteret.get_or_none(id=groupe_data.centre_interet_id)
    if not centre:
        raise HTTPException(status_code=404, detail="Centre d’intérêt introuvable")

    groupe = await Groupe.create(
        nom=groupe_data.nom,
        description=groupe_data.description,
        centreInteret=centre
    )

    # Optionnel : le créateur devient admin du groupe
    await UtilisateurGroupe.create(
        utilisateur=current_user,
        groupe=groupe,
        role="administrator",
        statut="actif"
    )

    return {"message": "Groupe créé", "groupe_id": groupe.id}


@router.post("/{groupe_id}/rejoindre")
async def rejoindre_groupe(
        groupe_id: int,
        current_user: Utilisateur = Depends(get_current_user)
):
    # Vérifie que le groupe existe
    groupe = await Groupe.get_or_none(id=groupe_id)
    if not groupe:
        raise HTTPException(status_code=404, detail="Groupe non trouvé")

    # Vérifie que l'utilisateur n'est pas déjà membre
    deja_membre = await UtilisateurGroupe.get_or_none(
        utilisateur=current_user, groupe=groupe
    )
    if deja_membre:
        raise HTTPException(status_code=400, detail="Déjà membre de ce groupe")

    # Ajoute l'utilisateur au groupe
    await UtilisateurGroupe.create(
        utilisateur=current_user,
        groupe=groupe,
        role="member",
        statut="actif"
    )

    return {"message": f"Utilisateur {current_user.nom} a rejoint le groupe {groupe.nom}"}


@router.post("/{groupe_id}/quitter")
async def quitter_groupe(
        groupe_id: int,
        current_user: Utilisateur = Depends(get_current_user)
):
    # Vérifie l'existence du lien utilisateur-groupe
    lien = await UtilisateurGroupe.get_or_none(
        utilisateur=current_user, groupe_id=groupe_id
    )
    if not lien:
        raise HTTPException(status_code=404, detail="Vous n'êtes pas membre de ce groupe")

    # Suppression ou mise à jour du statut
    await lien.delete()  # Ou bien lien.statut = "quitté"; await lien.save()

    return {"message": f"Utilisateur {current_user.nom} a quitté le groupe"}

@router.post("/{groupe_id}/changer-role")
async def changer_role_membre(
        groupe_id: int,
        payload: ChangementRole,
        current_user: Utilisateur = Depends(get_current_user)
):
    # Vérifie que le groupe existe
    groupe = await Groupe.get_or_none(id=groupe_id)
    if not groupe:
        raise HTTPException(status_code=404, detail="Groupe non trouvé")

    # Vérifie que current_user est admin dans ce groupe
    lien_admin = await UtilisateurGroupe.get_or_none(
        utilisateur=current_user, groupe=groupe
    )
    if not lien_admin or lien_admin.role != "administrator":
        raise HTTPException(status_code=403, detail="Seul un administrateur peut changer les rôles")

    # Récupère le lien du membre à modifier
    lien_membre = await UtilisateurGroupe.get_or_none(
        utilisateur_id=payload.utilisateur_id,
        groupe=groupe
    )
    if not lien_membre:
        raise HTTPException(status_code=404, detail="Membre non trouvé dans ce groupe")

    # Change le rôle
    lien_membre.role = payload.nouveau_role
    await lien_membre.save()

    return {"message": f"Le rôle de l'utilisateur {payload.utilisateur_id} a été mis à jour en {payload.nouveau_role}"}


@router.get("/centres-interet/{centre_id}/groupes")
async def groupes_par_centre(centre_id: int):
    centre = await CentreInteret.get_or_none(id=centre_id).prefetch_related("groupes")
    if not centre:
        raise HTTPException(status_code=404, detail="Centre d’intérêt introuvable")

    return [
        {"id": g.id, "nom": g.nom, "description": g.description}
        for g in centre.groupes
    ]

@router.get("/mes-groupes")
async def mes_groupes(current_user: Utilisateur = Depends(get_current_user)):
    liens = await UtilisateurGroupe.filter(
        utilisateur=current_user, 
        statut="actif"
    ).prefetch_related("groupe", "groupe__centreInteret")
    
    return [
        {
            "id": lien.groupe.id,
            "nom": lien.groupe.nom,
            "description": lien.groupe.description,
            "role": lien.role,
            "centre_interet": {
                "id": lien.groupe.centreInteret.id,
                "nom": lien.groupe.centreInteret.nom
            }
        }
        for lien in liens
    ]

@router.get("/all")
async def get_all_groups():
    """Get all groups with their members"""
    try:
        # Get all groups with their centre d'intérêt
        groups = await Groupe.all().prefetch_related("centreInteret")
        
        result = []
        for group in groups:
            # Get all members for this group
            members_links = await UtilisateurGroupe.filter(
                groupe=group,
                statut="actif"
            ).prefetch_related("utilisateur")
            
            # Format members data
            members = [
                {
                    "id": link.utilisateur.id,
                    "nom": link.utilisateur.nom,
                    "prenom": link.utilisateur.prenom,
                    "email": link.utilisateur.email,
                    "filiere": link.utilisateur.filiere.value if link.utilisateur.filiere else None,
                    "niveau": link.utilisateur.niveau.value if link.utilisateur.niveau else None,
                    "avatar": link.utilisateur.avatar
                }
                for link in members_links
            ]
            
            # Format group data
            group_data = {
                "id": group.id,
                "nom": group.nom,
                "description": group.description,
                "centre_interet": group.centreInteret.titre if group.centreInteret else None,
                "membres": members,
                "nombre_membres": len(members)
            }
            
            result.append(group_data)
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des groupes: {str(e)}")
