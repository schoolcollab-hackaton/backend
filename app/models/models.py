from tortoise.models import Model
from tortoise import fields
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class Utilisateur(Model):
    id = fields.IntField(pk=True)
    nom = fields.CharField(max_length=100)
    prenom = fields.CharField(max_length=100)
    email = fields.CharField(max_length=200, unique=True)
    password = fields.TextField()
    role = fields.CharField(max_length=50)
    score = fields.IntField(default=0)
    avatar = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "utilisateur"

class CentreInteret(Model):
    id = fields.IntField(pk=True)
    titre = fields.CharField(max_length=200)

    class Meta:
        table = "centreInteret"

class Publication(Model):
    id = fields.IntField(pk=True)
    contenu = fields.TextField()
    imageURL = fields.TextField(null=True)
    date = fields.DatetimeField(auto_now_add=True)
    type = fields.CharField(max_length=50)
    auteur = fields.ForeignKeyField('models.Utilisateur', related_name='publications')

    class Meta:
        table = "publication"

class Groupe(Model):
    id = fields.IntField(pk=True)
    nom = fields.CharField(max_length=200)
    description = fields.TextField()
    centreInteret = fields.ForeignKeyField('models.CentreInteret', related_name='groupes')

    class Meta:
        table = "groupe"

class Parrainage(Model):
    id = fields.IntField(pk=True)
    statut = fields.CharField(max_length=50, default='Pending')  # Pending, Approved, Completed, Cancelled
    dateDemande = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "parrainage"

class UtilisateurParrainage(Model):
    id = fields.IntField(pk=True)
    utilisateur = fields.ForeignKeyField('models.Utilisateur', related_name='parrainages')
    parrainage = fields.ForeignKeyField('models.Parrainage', related_name='utilisateurs')
    role = fields.CharField(max_length=50)  # "parrain", "filleul"

    class Meta:
        table = "utilisateurParrainage"

class UtilisateurCentreInteret(Model):
    id = fields.IntField(pk=True)
    utilisateur = fields.ForeignKeyField('models.Utilisateur', related_name='centres_interet')
    centreInteret = fields.ForeignKeyField('models.CentreInteret', related_name='utilisateurs')

    class Meta:
        table = "utilisateurCentreInteret"

class Competence(Model):
    id = fields.IntField(pk=True)
    nom = fields.CharField(max_length=200)
    description = fields.TextField()

    class Meta:
        table = "competence"

class DemandeSoutien(Model):
    id = fields.IntField(pk=True)
    demandeur = fields.ForeignKeyField('models.Utilisateur', related_name='demandes_soutien')
    helper = fields.ForeignKeyField('models.Utilisateur', related_name='aides_fournies', null=True)
    competence = fields.ForeignKeyField('models.Competence', related_name='demandes')
    statut = fields.CharField(max_length=50, default='Pending')  # Pending, Approved, Completed, Cancelled
    dateDemande = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "demandeSoutien"

class ScoreAction(Model):
    id = fields.IntField(pk=True)
    typeAction = fields.CharField(max_length=100)
    points = fields.IntField()
    date = fields.DatetimeField(auto_now_add=True)
    utilisateur = fields.ForeignKeyField('models.Utilisateur', related_name='score_actions')

    class Meta:
        table = "scoreAction"

class UtilisateurPublication(Model):
    id = fields.IntField(pk=True)
    utilisateur = fields.ForeignKeyField('models.Utilisateur', related_name='interactions_publications')
    publication = fields.ForeignKeyField('models.Publication', related_name='interactions')
    typeInteraction = fields.CharField(max_length=50)  # like, comment, etc.
    dateInteraction = fields.DatetimeField(auto_now_add=True)
    statut = fields.CharField(max_length=50)

    class Meta:
        table = "utilisateurPublication"

class UtilisateurGroupe(Model):
    id = fields.IntField(pk=True)
    utilisateur = fields.ForeignKeyField('models.Utilisateur', related_name='groupes_membre')
    groupe = fields.ForeignKeyField('models.Groupe', related_name='membres')
    role = fields.CharField(max_length=50)  # member, administrator, moderator
    dateJoined = fields.DatetimeField(auto_now_add=True)
    statut = fields.CharField(max_length=50)

    class Meta:
        table = "utilisateurGroupe"

class UtilisateurCompetence(Model):
    id = fields.IntField(pk=True)
    utilisateur = fields.ForeignKeyField('models.Utilisateur', related_name='competences')
    competence = fields.ForeignKeyField('models.Competence', related_name='utilisateurs')
    niveau = fields.CharField(max_length=50)
    dateObtention = fields.DatetimeField(auto_now_add=True)
    statut = fields.CharField(max_length=50)

    class Meta:
        table = "utilisateurCompetence"

class Message(Model):
    id = fields.IntField(pk=True)
    contenu = fields.TextField()
    date = fields.DatetimeField(auto_now_add=True)
    expediteur = fields.ForeignKeyField('models.Utilisateur', related_name='messages_envoyes')
    destinataire = fields.ForeignKeyField('models.Utilisateur', related_name='messages_recus')
    estToxique = fields.BooleanField(default=False)

    class Meta:
        table = "message"

class BaseConnaissance(Model):
    id = fields.IntField(pk=True)
    categorie = fields.CharField(max_length=100)
    question = fields.TextField()
    reponse = fields.TextField()
    tags = fields.CharField(max_length=500)  # ex : "connexion, mot de passe, compte"
    dateCreation = fields.DatetimeField(auto_now_add=True)
    statut = fields.CharField(max_length=50, default='active')  # active, inactive, à valider

    class Meta:
        table = "baseConnaissance"

class HistoriqueChatbot(Model):
    id = fields.IntField(pk=True)
    utilisateur = fields.ForeignKeyField('models.Utilisateur', related_name='historique_chatbot')
    question = fields.TextField()
    reponse = fields.TextField()
    dateInteraction = fields.DatetimeField(auto_now_add=True)
    referenceBase = fields.ForeignKeyField('models.BaseConnaissance', related_name='historiques', null=True)

    class Meta:
        table = "historiqueChatbot"

# Pydantic schemas for API responses
class UtilisateurSchema(BaseModel):
    id: int
    nom: str
    prenom: str
    email: str
    role: str
    score: int
    avatar: Optional[str] = None

    class Config:
        from_attributes = True

class PublicationSchema(BaseModel):
    id: int
    contenu: str
    imageURL: Optional[str] = None
    date: datetime
    type: str
    auteur_id: int

    class Config:
        from_attributes = True

class MessageSchema(BaseModel):
    id: int
    contenu: str
    date: datetime
    expediteur_id: int
    destinataire_id: int
    estToxique: bool

    class Config:
        from_attributes = True