from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from ..models.models import Message, MessageSchema, Utilisateur
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..utils import verify_token

router = APIRouter(prefix="/messages", tags=["messages"])
security = HTTPBearer()

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

@router.post("/", response_model=MessageSchema)
async def create_message(
    destinataire_id: int,
    contenu: str,
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Create a new message
    """
    try:
        # Check if recipient exists
        destinataire = await Utilisateur.get_or_none(id=destinataire_id)
        if not destinataire:
            raise HTTPException(
                status_code=404,
                detail="Recipient not found"
            )

        # Create message
        message = await Message.create(
            contenu=contenu,
            expediteur=current_user,
            destinataire=destinataire,
            estToxique=False
        )

        return MessageSchema(
            id=message.id,
            contenu=message.contenu,
            date=message.date,
            expediteur_id=message.expediteur_id,
            destinataire_id=message.destinataire_id,
            estToxique=message.estToxique
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating message: {str(e)}"
        )

@router.get("/received", response_model=List[MessageSchema])
async def get_received_messages(
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Get all messages received by the current user
    """
    try:
        messages = await Message.filter(destinataire=current_user).order_by('-date')
        return [MessageSchema(
            id=msg.id,
            contenu=msg.contenu,
            date=msg.date,
            expediteur_id=msg.expediteur_id,
            destinataire_id=msg.destinataire_id,
            estToxique=msg.estToxique
        ) for msg in messages]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching received messages: {str(e)}"
        )

@router.get("/sent", response_model=List[MessageSchema])
async def get_sent_messages(
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Get all messages sent by the current user
    """
    try:
        messages = await Message.filter(expediteur=current_user).order_by('-date')
        return [MessageSchema(
            id=msg.id,
            contenu=msg.contenu,
            date=msg.date,
            expediteur_id=msg.expediteur_id,
            destinataire_id=msg.destinataire_id,
            estToxique=msg.estToxique
        ) for msg in messages]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching sent messages: {str(e)}"
        )

@router.get("/conversation/{other_user_id}", response_model=List[MessageSchema])
async def get_conversation(
    other_user_id: int,
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Get conversation between current user and another user
    """
    try:
        # Check if other user exists
        other_user = await Utilisateur.get_or_none(id=other_user_id)
        if not other_user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # Get messages between the two users
        messages = await Message.filter(
            (
                (Message.expediteur == current_user) & 
                (Message.destinataire == other_user)
            ) |
            (
                (Message.expediteur == other_user) & 
                (Message.destinataire == current_user)
            )
        ).order_by('date')

        return [MessageSchema(
            id=msg.id,
            contenu=msg.contenu,
            date=msg.date,
            expediteur_id=msg.expediteur_id,
            destinataire_id=msg.destinataire_id,
            estToxique=msg.estToxique
        ) for msg in messages]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching conversation: {str(e)}"
        )

@router.delete("/{message_id}")
async def delete_message(
    message_id: int,
    current_user: Utilisateur = Depends(get_current_user)
):
    """
    Delete a message
    """
    try:
        message = await Message.get_or_none(id=message_id)
        if not message:
            raise HTTPException(
                status_code=404,
                detail="Message not found"
            )

        await message.delete()
        return {"message": "Message deleted successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting message: {str(e)}"
        ) 