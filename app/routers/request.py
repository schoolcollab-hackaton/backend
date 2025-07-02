from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.models.models import UtilisateurRequest, Utilisateur, RequestTypeEnum, UtilisateurMate
from app.routers.auth import get_current_user

router = APIRouter(prefix="/requests", tags=["requests"])

# Pydantic models for requests
class CreateRequest(BaseModel):
    type: RequestTypeEnum
    receiver_id: int
    message: Optional[str] = None

class RequestResponse(BaseModel):
    id: int
    type: RequestTypeEnum
    message: Optional[str]
    sender_id: int
    receiver_id: int
    status: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True

class RequestUpdate(BaseModel):
    status: str

@router.post("/", response_model=RequestResponse)
async def create_request(
    request_data: CreateRequest,
    current_user: Utilisateur = Depends(get_current_user)
):
    """Create a new request"""
    # Check if receiver exists
    receiver = await Utilisateur.get_or_none(id=request_data.receiver_id)
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver not found"
        )
    
    # Check if user is trying to send request to themselves
    if current_user.id == request_data.receiver_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send request to yourself"
        )
    
    # Create the request
    request = await UtilisateurRequest.create(
        type=request_data.type,
        message=request_data.message,
        sender_id=current_user.id,
        receiver_id=request_data.receiver_id,
        status="pending"
    )
    
    return RequestResponse(
        id=request.id,
        type=request.type,
        message=request.message,
        sender_id=request.sender_id,
        receiver_id=request.receiver_id,
        status="pending",
        created_at=str(request.created_at),
        updated_at=str(request.updated_at)
    )

@router.put("/{request_id}/accept")
async def accept_request(
    request_id: int,
    current_user: Utilisateur = Depends(get_current_user)
):
    """Accept a request"""
    request = await UtilisateurRequest.get_or_none(id=request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    # Check if current user is the receiver
    if request.receiver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only accept requests sent to you"
        )
    
    # Update request status
    request.status = "accepted"
    await request.save()
    
    # Add both users as mates to each other
    try:
        # Add receiver as mate of sender
        await UtilisateurMate.get_or_create(
            utilisateur_id=request.sender_id,
            mate_id=current_user.id
        )
        
        # Add sender as mate of receiver
        await UtilisateurMate.get_or_create(
            utilisateur_id=current_user.id,
            mate_id=request.sender_id
        )
    except Exception as e:
        # Continue even if mate relationship already exists
        pass
    
    return {"message": "Request accepted successfully and users added as mates"}

@router.put("/{request_id}/reject")
async def reject_request(
    request_id: int,
    current_user: Utilisateur = Depends(get_current_user)
):
    """Reject a request"""
    request = await UtilisateurRequest.get_or_none(id=request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    # Check if current user is the receiver
    if request.receiver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only reject requests sent to you"
        )
    
    # Update request status
    request.status = "rejected"
    await request.save()
    
    return {"message": "Request rejected successfully"}

@router.get("/sent", response_model=List[RequestResponse])
async def get_sent_requests(
    current_user: Utilisateur = Depends(get_current_user)
):
    """Get all requests sent by current user"""
    requests = await UtilisateurRequest.filter(sender_id=current_user.id).all()
    
    return [
        RequestResponse(
            id=request.id,
            type=request.type,
            message=request.message,
            sender_id=request.sender_id,
            receiver_id=request.receiver_id,
            status=getattr(request, 'status', 'pending'),
            created_at=str(request.created_at),
            updated_at=str(request.updated_at)
        )
        for request in requests
    ]

@router.get("/received", response_model=List[RequestResponse])
async def get_received_requests(
    current_user: Utilisateur = Depends(get_current_user)
):
    """Get all requests received by current user"""
    requests = await UtilisateurRequest.filter(receiver_id=current_user.id).all()
    
    return [
        RequestResponse(
            id=request.id,
            type=request.type,
            message=request.message,
            sender_id=request.sender_id,
            receiver_id=request.receiver_id,
            status=getattr(request, 'status', 'pending'),
            created_at=str(request.created_at),
            updated_at=str(request.updated_at)
        )
        for request in requests
    ]

@router.get("/all", response_model=List[RequestResponse])
async def get_all_requests(
    current_user: Utilisateur = Depends(get_current_user)
):
    """Get all requests (both sent and received) by current user"""
    sent_requests = await UtilisateurRequest.filter(sender_id=current_user.id).all()
    received_requests = await UtilisateurRequest.filter(receiver_id=current_user.id).all()
    
    all_requests = sent_requests + received_requests
    
    return [
        RequestResponse(
            id=request.id,
            type=request.type,
            message=request.message,
            sender_id=request.sender_id,
            receiver_id=request.receiver_id,
            status=getattr(request, 'status', 'pending'),
            created_at=str(request.created_at),
            updated_at=str(request.updated_at)
        )
        for request in all_requests
    ]