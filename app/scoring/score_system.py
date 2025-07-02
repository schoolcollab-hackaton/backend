from enum import Enum
from typing import Dict
from app.models.models import Utilisateur, ScoreAction


class ActionType(str, Enum):
    """Types d'actions qui donnent des points aux utilisateurs"""

    # Actions de parrainage
    PARRAINAGE_CREATION = "parrainage_creation"  # Créer une demande de parrainage
    PARRAINAGE_ACCEPTATION = "parrainage_acceptation"  # Accepter une demande de parrainage
    PARRAINAGE_COMPLETION = "parrainage_completion"  # Compléter un parrainage




    # Actions de soutien
    SOUTIEN_OFFRIR = "soutien_offrir"  # Offrir du soutien
    SOUTIEN_RECEVOIR = "soutien_recevoir"  # Recevoir du soutien




# Points attribués pour chaque type d'action
POINTS_PAR_ACTION: Dict[ActionType, int] = {
    ActionType.PARRAINAGE_CREATION: 5,
    ActionType.PARRAINAGE_ACCEPTATION: 10,
    ActionType.PARRAINAGE_COMPLETION: 20,





    ActionType.SOUTIEN_OFFRIR: 10,
    ActionType.SOUTIEN_RECEVOIR: 3,




}


async def ajouter_points(utilisateur_id: int, type_action: ActionType) -> int:
    """
    Ajoute des points à un utilisateur pour une action spécifique
    et retourne le nouveau score total.

    Args:
        utilisateur_id: ID de l'utilisateur
        type_action: Type d'action effectuée

    Returns:
        Le nouveau score total de l'utilisateur
    """
    # Vérifier si l'action existe
    if type_action not in POINTS_PAR_ACTION:
        raise ValueError(f"Type d'action non reconnu: {type_action}")

    points = POINTS_PAR_ACTION[type_action]

    # Récupérer l'utilisateur
    utilisateur = await Utilisateur.get(id=utilisateur_id)

    # Créer l'enregistrement ScoreAction
    await ScoreAction.create(
        typeAction=type_action,
        points=points,
        utilisateur_id=utilisateur_id
    )

    # Mettre à jour le score de l'utilisateur
    utilisateur.score += points
    await utilisateur.save()

    return utilisateur.score


async def calculer_score_total(utilisateur_id: int) -> int:
    """
    Recalcule le score total d'un utilisateur à partir de son historique d'actions.
    Utile pour corriger ou synchroniser le score.

    Args:
        utilisateur_id: ID de l'utilisateur

    Returns:
        Le score total recalculé
    """
    actions = await ScoreAction.filter(utilisateur_id=utilisateur_id)
    score_total = sum(action.points for action in actions)

    # Mettre à jour le score dans la base de données
    utilisateur = await Utilisateur.get(id=utilisateur_id)
    utilisateur.score = score_total
    await utilisateur.save()

    return score_total