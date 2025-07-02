from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.models.models import (
    Publication,
    Utilisateur,
    UtilisateurPublication,
    PublicationSchema,
)
from app.utils import get_current_user
from pydantic import BaseModel
from datetime import datetime


class PublicationCreate(BaseModel):
    titre: str
    contenu: str
    imageURL: str = None
    type: str


class PublicationUpdate(BaseModel):
    titre: str = None
    contenu: str = None
    imageURL: str = None
    type: str = None


class CommentCreate(BaseModel):
    contenu: str


class CommentResponse(BaseModel):
    id: int
    utilisateur_id: int
    publication_id: int
    contenu: str
    dateInteraction: datetime


router = APIRouter(prefix="/publications", tags=["publications"])


@router.post("/", response_model=PublicationSchema)
async def create_publication(
    data: PublicationCreate, current_user: Utilisateur = Depends(get_current_user)
):
    pub = await Publication.create(
        titre=data.titre,
        contenu=data.contenu,
        imageURL=data.imageURL,
        type=data.type,
        auteur=current_user,
    )
    return PublicationSchema(
        id=pub.id,
        titre=pub.titre,
        contenu=pub.contenu,
        imageURL=pub.imageURL,
        date=pub.date,
        type=pub.type,
        auteur_id=pub.auteur_id,
    )


@router.get("/", response_model=List[PublicationSchema])
async def list_publications():
    pubs = await Publication.all().order_by("-date")
    return [
        PublicationSchema(
            id=p.id,
            titre=p.titre,
            contenu=p.contenu,
            imageURL=p.imageURL,
            date=p.date,
            type=p.type,
            auteur_id=p.auteur_id,
        )
        for p in pubs
    ]


@router.get("/{pub_id}", response_model=PublicationSchema)
async def get_publication(pub_id: int):
    pub = await Publication.get_or_none(id=pub_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")
    return PublicationSchema(
        id=pub.id,
        titre=pub.titre,
        contenu=pub.contenu,
        imageURL=pub.imageURL,
        date=pub.date,
        type=pub.type,
        auteur_id=pub.auteur_id,
    )


@router.put("/{pub_id}", response_model=PublicationSchema)
async def update_publication(
    pub_id: int,
    data: PublicationUpdate,
    current_user: Utilisateur = Depends(get_current_user),
):
    pub = await Publication.get_or_none(id=pub_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")
    if pub.auteur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    update_data = data.dict(exclude_unset=True)
    for k, v in update_data.items():
        setattr(pub, k, v)
    await pub.save()
    return PublicationSchema(
        id=pub.id,
        titre=pub.titre,
        contenu=pub.contenu,
        imageURL=pub.imageURL,
        date=pub.date,
        type=pub.type,
        auteur_id=pub.auteur_id,
    )


@router.delete("/{pub_id}")
async def delete_publication(
    pub_id: int, current_user: Utilisateur = Depends(get_current_user)
):
    pub = await Publication.get_or_none(id=pub_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")
    if pub.auteur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    await pub.delete()
    return {"message": "Publication deleted"}


@router.post("/{pub_id}/like")
async def like_publication(
    pub_id: int, current_user: Utilisateur = Depends(get_current_user)
):
    pub = await Publication.get_or_none(id=pub_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")
    existing = await UtilisateurPublication.get_or_none(
        utilisateur=current_user, publication=pub, typeInteraction="like"
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already liked")
    await UtilisateurPublication.create(
        utilisateur=current_user,
        publication=pub,
        typeInteraction="like",
        statut="active",
    )
    return {"message": "Publication liked"}


@router.post("/{pub_id}/unlike")
async def unlike_publication(
    pub_id: int, current_user: Utilisateur = Depends(get_current_user)
):
    pub = await Publication.get_or_none(id=pub_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")
    like = await UtilisateurPublication.get_or_none(
        utilisateur=current_user, publication=pub, typeInteraction="like"
    )
    if not like:
        raise HTTPException(status_code=400, detail="Not liked yet")
    await like.delete()
    return {"message": "Like removed"}


@router.get("/{pub_id}/likes")
async def get_likes_count(pub_id: int):
    pub = await Publication.get_or_none(id=pub_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")
    count = await UtilisateurPublication.filter(
        publication=pub, typeInteraction="like"
    ).count()
    return {"likes": count}


@router.post("/{pub_id}/comment", response_model=CommentResponse)
async def add_comment(
    pub_id: int,
    data: CommentCreate,
    current_user: Utilisateur = Depends(get_current_user),
):
    pub = await Publication.get_or_none(id=pub_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")
    comment = await UtilisateurPublication.create(
        utilisateur=current_user,
        publication=pub,
        typeInteraction="comment",
        statut="active",
        dateInteraction=datetime.utcnow(),
    )
    comment.statut = data.contenu
    await comment.save()
    return CommentResponse(
        id=comment.id,
        utilisateur_id=current_user.id,
        publication_id=pub.id,
        contenu=comment.statut,
        dateInteraction=comment.dateInteraction,
    )


@router.get("/{pub_id}/comments", response_model=List[CommentResponse])
async def list_comments(pub_id: int):
    pub = await Publication.get_or_none(id=pub_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")
    comments = await UtilisateurPublication.filter(
        publication=pub, typeInteraction="comment"
    ).order_by("dateInteraction")
    return [
        CommentResponse(
            id=c.id,
            utilisateur_id=c.utilisateur_id,
            publication_id=c.publication_id,
            contenu=c.statut,
            dateInteraction=c.dateInteraction,
        )
        for c in comments
    ]


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int, current_user: Utilisateur = Depends(get_current_user)
):
    comment = await UtilisateurPublication.get_or_none(
        id=comment_id, typeInteraction="comment"
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.utilisateur_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    await comment.delete()
    return {"message": "Comment deleted"}
