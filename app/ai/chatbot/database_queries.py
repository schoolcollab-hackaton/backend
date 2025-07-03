from tortoise.models import Model
from app.models.models import (
    Groupe, Utilisateur, UtilisateurGroupe, 
    DemandeSoutien, Parrainage, UtilisateurParrainage,
    CentreInteret, Competence, UtilisateurRole, RoleEnum
)
from typing import List, Dict, Optional
import json

class DatabaseQueries:
    
    @staticmethod
    async def find_groups(user_id: int = None, centre_interet: str = None) -> List[Dict]:
        query = Groupe.all().prefetch_related('centreInteret')
        
        if centre_interet:
            query = query.filter(centreInteret__titre__icontains=centre_interet)
        
        groupes = await query
        
        result = []
        for groupe in groupes:
            membres_count = await UtilisateurGroupe.filter(groupe=groupe).count()
            result.append({
                "id": groupe.id,
                "nom": groupe.nom,
                "description": groupe.description,
                "centre_interet": groupe.centreInteret.titre if groupe.centreInteret else None,
                "nombre_membres": membres_count
            })
        
        return result
    
    @staticmethod
    async def create_demande_soutien(user_id: int, competence_name: str) -> Dict:
        try:
            competence = await Competence.filter(nom__icontains=competence_name).first()
            if not competence:
                competence = await Competence.create(
                    nom=competence_name,
                    description=f"Compétence en {competence_name}"
                )
            
            demande = await DemandeSoutien.create(
                demandeur_id=user_id,
                competence=competence,
                statut="Pending"
            )
            
            return {
                "id": demande.id,
                "competence": competence.nom,
                "statut": demande.statut,
                "date_demande": demande.dateDemande.isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    async def find_parrains(user_id: int = None, filiere: str = None) -> List[Dict]:
        query = Utilisateur.all()
        
        if filiere:
            query = query.filter(filiere=filiere)
        
        mentor_users = await UtilisateurRole.filter(role=RoleEnum.MENTOR).prefetch_related('utilisateur')
        mentor_ids = [ur.utilisateur.id for ur in mentor_users]
        
        query = query.filter(id__in=mentor_ids)
        
        if user_id:
            query = query.exclude(id=user_id)
        
        parrains = await query
        
        result = []
        for parrain in parrains:
            result.append({
                "id": parrain.id,
                "nom": parrain.nom,
                "prenom": parrain.prenom,
                "filiere": parrain.filiere,
                "niveau": parrain.niveau,
                "score": parrain.score
            })
        
        return result
    
    @staticmethod
    async def create_parrain_request(user_id: int, parrain_id: int) -> Dict:
        try:
            existing_request = await UtilisateurParrainage.filter(
                utilisateur_id=user_id,
                parrainage__utilisateurs__utilisateur_id=parrain_id,
                role="filleul"
            ).first()
            
            if existing_request:
                return {"error": "Une demande de parrainage existe déjà avec ce parrain"}
            
            parrainage = await Parrainage.create(statut="Pending")
            
            await UtilisateurParrainage.create(
                utilisateur_id=user_id,
                parrainage=parrainage,
                role="filleul"
            )
            
            await UtilisateurParrainage.create(
                utilisateur_id=parrain_id,
                parrainage=parrainage,
                role="parrain"
            )
            
            return {
                "id": parrainage.id,
                "statut": parrainage.statut,
                "date_demande": parrainage.dateDemande.isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    async def get_user_info(user_id: int) -> Optional[Dict]:
        try:
            user = await Utilisateur.get(id=user_id)
            roles = await UtilisateurRole.filter(utilisateur=user).all()
            
            return {
                "id": user.id,
                "nom": user.nom,
                "prenom": user.prenom,
                "email": user.email,
                "filiere": user.filiere,
                "niveau": user.niveau,
                "score": user.score,
                "roles": [role.role for role in roles]
            }
        except Exception as e:
            return None
    
    @staticmethod
    async def get_competences() -> List[Dict]:
        competences = await Competence.all()
        return [{"id": c.id, "nom": c.nom, "description": c.description} for c in competences]
    
    @staticmethod
    async def get_centres_interet() -> List[Dict]:
        centres = await CentreInteret.all()
        return [{"id": c.id, "titre": c.titre} for c in centres]
    
    @staticmethod
    async def find_skill_swap_partners(user_id: int, limit: int = 5) -> List[Dict]:
        """Find skill swap partners using the recommendation service"""
        try:
            # Import here to avoid circular imports
            from app.ai.recommendation_service import RecommendationService
            
            recommendation_service = RecommendationService()
            recommendations = await recommendation_service.skill_swap(user_id, limit)
            
            # Format the recommendations for chatbot response
            partners = []
            for rec in recommendations:
                partner = {
                    "id": rec.get("id"),
                    "nom": rec.get("nom"),
                    "prenom": rec.get("prenom"),
                    "filiere": rec.get("filiere"),
                    "niveau": rec.get("niveau"),
                    "swap_score": round(rec.get("swap_score", 0), 2),
                    "skills_they_offer": rec.get("swap_details", {}).get("skills_they_offer", []),
                    "skills_you_offer": rec.get("swap_details", {}).get("skills_you_offer", []),
                    "mutual_benefits": rec.get("swap_details", {}).get("mutual_benefits", [])
                }
                partners.append(partner)
            
            return partners
            
        except Exception as e:
            print(f"Error finding skill swap partners: {e}")
            return []