from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Union
from .chatbot import FrenchChatbot
from app.models.models import HistoriqueChatbot, Utilisateur
import json

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

class ChatMessage(BaseModel):
    message: str
    user_id: int

class ChatResponse(BaseModel):
    intent: str
    confidence: float
    message: str
    data: Optional[Union[dict, List[dict]]] = None
    suggestions: Optional[List[str]] = None

chatbot = FrenchChatbot()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(chat_message: ChatMessage):
    try:
        # Verify user exists
        user = await Utilisateur.get_or_none(id=chat_message.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        # Process message with chatbot
        response = await chatbot.process_message(chat_message.message, chat_message.user_id)
        
        # Get suggestions for next actions
        suggestions = await chatbot.get_suggestions(chat_message.user_id)
        
        # Save to history
        await HistoriqueChatbot.create(
            utilisateur=user,
            question=chat_message.message,
            reponse=response["message"]
        )
        # Ensure data is properly formatted
        data = response.get("data")
        print(f"Data received: {data}")
        
        return ChatResponse(
            intent=response["intent"],
            confidence=response["confidence"],
            message=response["message"],
            data=data,
            suggestions=suggestions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur: {str(e)}")

@router.get("/history/{user_id}")
async def get_chat_history(user_id: int, limit: int = 10):
    try:
        user = await Utilisateur.get_or_none(id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        history = await HistoriqueChatbot.filter(utilisateur=user).order_by('-dateInteraction').limit(limit)
        
        return [
            {
                "id": h.id,
                "question": h.question,
                "reponse": h.reponse,
                "date": h.dateInteraction.isoformat()
            }
            for h in history
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur: {str(e)}")

@router.get("/suggestions/{user_id}")
async def get_suggestions(user_id: int):
    try:
        user = await Utilisateur.get_or_none(id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        suggestions = await chatbot.get_suggestions(user_id)
        
        return {"suggestions": suggestions}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur: {str(e)}")

@router.get("/intents")
async def get_available_intents():
    """Get all available intents and their example phrases"""
    return {
        "intents": {
            "find_groups": {
                "description": "Chercher et trouver des groupes",
                "examples": [
                    "Je veux trouver des groupes",
                    "Montrez-moi les groupes",
                    "Groupes disponibles"
                ]
            },
            "demande_soutien": {
                "description": "Demander de l'aide ou du soutien",
                "examples": [
                    "J'ai besoin d'aide",
                    "Je demande de l'aide",
                    "Pouvez-vous m'aider?"
                ]
            },
            "search_parrain": {
                "description": "Chercher un parrain ou mentor",
                "examples": [
                    "Je cherche un parrain",
                    "Où trouver un mentor?",
                    "J'ai besoin d'un parrain"
                ]
            },
            "ask_for_parrain": {
                "description": "Proposer ses services de parrainage",
                "examples": [
                    "Je veux devenir parrain",
                    "Comment être mentor?",
                    "Je peux aider comme parrain"
                ]
            },
            "find_skill_swap": {
                "description": "Chercher des partenaires d'échange de compétences",
                "examples": [
                    "Je cherche un échange de compétences",
                    "Skill swap",
                    "Je veux échanger mes compétences",
                    "Partenaires d'apprentissage"
                ]
            }
        }
    }