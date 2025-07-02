from fastapi import APIRouter, HTTPException, Depends
from typing import List
from pydantic import BaseModel
from ..models.models import Contact, ContactSchema, ContactCreateSchema
from ..ai.ai_service import AIService

router = APIRouter(prefix="/contact", tags=["contact"])

class ContactCreationResponse(BaseModel):
    message: str
    contact_id: int

@router.post("/", response_model=ContactCreationResponse)
async def create_contact(contact_data: ContactCreateSchema):
    """
    Create a new contact message
    """
    try:
        # Check for toxic content using AI service
        ai_service = AIService()
        message_moderation = await ai_service.moderate_content(contact_data.message)
        print(f"Moderation result: {message_moderation}")
        if message_moderation['is_toxic']:
            raise HTTPException(
                status_code=400, 
                detail="Message contains inappropriate content and cannot be submitted"
            )
        
        # Create contact entry
        contact = await Contact.create(
            nom=contact_data.nom,
            email=contact_data.email,
            sujet=contact_data.sujet,
            message=contact_data.message
        )
        
        return ContactCreationResponse(
            message="Contact message created successfully",
            contact_id=contact.id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating contact: {str(e)}")

@router.get("/", response_model=List[ContactSchema])
async def get_all_contacts():
    """
    Get all contact messages (admin only)
    """
    try:
        contacts = await Contact.all().order_by('-dateCreation')
        return [ContactSchema(
            id=contact.id,
            nom=contact.nom,
            email=contact.email,
            sujet=contact.sujet,
            message=contact.message,
            dateCreation=contact.dateCreation,
            statut=contact.statut
        ) for contact in contacts]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching contacts: {str(e)}")

@router.get("/{contact_id}", response_model=ContactSchema)
async def get_contact(contact_id: int):
    """
    Get a specific contact message by ID
    """
    try:
        contact = await Contact.get_or_none(id=contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        return ContactSchema(
            id=contact.id,
            nom=contact.nom,
            email=contact.email,
            sujet=contact.sujet,
            message=contact.message,
            dateCreation=contact.dateCreation,
            statut=contact.statut
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching contact: {str(e)}")

@router.patch("/{contact_id}/status")
async def update_contact_status(contact_id: int, new_status: str):
    """
    Update contact status (nouveau, lu, traite)
    """
    try:
        contact = await Contact.get_or_none(id=contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        if new_status not in ['nouveau', 'lu', 'traite']:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        contact.statut = new_status
        await contact.save()
        
        return {"message": f"Contact status updated to {new_status}", "contact_id": contact_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating contact status: {str(e)}")

@router.delete("/{contact_id}")
async def delete_contact(contact_id: int):
    """
    Delete a contact message
    """
    try:
        contact = await Contact.get_or_none(id=contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        await contact.delete()
        return {"message": "Contact deleted successfully", "contact_id": contact_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting contact: {str(e)}")

@router.get("/stats/summary")
async def get_contact_stats():
    """
    Get contact statistics
    """
    try:
        total_contacts = await Contact.all().count()
        nouveau_count = await Contact.filter(statut='nouveau').count()
        lu_count = await Contact.filter(statut='lu').count()
        traite_count = await Contact.filter(statut='traite').count()
        
        return {
            "total_contacts": total_contacts,
            "nouveau": nouveau_count,
            "lu": lu_count,
            "traite": traite_count
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching contact stats: {str(e)}")