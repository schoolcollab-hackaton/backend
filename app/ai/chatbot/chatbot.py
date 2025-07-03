from .intent_classifier import IntentClassifier
from .database_queries import DatabaseQueries
from typing import Dict, List, Optional
import json
import re

class FrenchChatbot:
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.db_queries = DatabaseQueries()
        
        self.responses = {
            "find_groups": {
                "no_results": "Je n'ai trouvé aucun groupe correspondant à votre recherche.",
                "success": "Voici les groupes que j'ai trouvés :",
                "error": "Désolé, je n'ai pas pu récupérer les groupes pour le moment."
            },
            "demande_soutien": {
                "success": "Votre demande de soutien a été créée avec succès !",
                "error": "Je n'ai pas pu créer votre demande de soutien.",
                "missing_competence": "Pouvez-vous préciser dans quel domaine vous avez besoin d'aide ?"
            },
            "search_parrain": {
                "no_results": "Je n'ai trouvé aucun parrain disponible pour le moment.",
                "success": "Voici les parrains disponibles :",
                "error": "Je n'ai pas pu récupérer la liste des parrains."
            },
            "ask_for_parrain": {
                "success": "Votre demande de parrainage a été envoyée !",
                "error": "Je n'ai pas pu envoyer votre demande de parrainage.",
                "missing_parrain": "Pouvez-vous me dire quel parrain vous intéresse ?"
            },
            "find_skill_swap": {
                "success": "Voici des partenaires d'échange de compétences recommandés pour vous :",
                "no_results": "Je n'ai trouvé aucun partenaire d'échange de compétences pour le moment.",
                "error": "Je n'ai pas pu trouver de partenaires d'échange de compétences."
            },
            "unknown": "Je ne comprends pas votre demande. Pouvez-vous reformuler ?"
        }
    
    def extract_keywords(self, text: str) -> List[str]:
        text = text.lower()
        keywords = []
        
        # Extract potential subject/competence keywords
        competence_patterns = [
            r"en (\w+)",
            r"pour (\w+)",
            r"dans (\w+)",
            r"sur (\w+)",
            r"avec (\w+)"
        ]
        
        for pattern in competence_patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)
        
        # Extract specific terms
        terms = text.split()
        tech_terms = ["python", "javascript", "react", "django", "fastapi", "sql", "ai", "machine learning", "data science"]
        keywords.extend([term for term in terms if term in tech_terms])
        
        return list(set(keywords))
    
    def extract_numbers(self, text: str) -> List[int]:
        numbers = re.findall(r'\d+', text)
        return [int(num) for num in numbers]
    
    async def process_message(self, message: str, user_id: int) -> Dict:
        try:
            intent, confidence = self.intent_classifier.classify_intent(message)
            
            response = {
                "intent": intent,
                "confidence": confidence,
                "message": "",
                "data": None
            }
            
            if intent == "find_groups":
                response = await self._handle_find_groups(message, user_id, response)
            elif intent == "demande_soutien":
                response = await self._handle_demande_soutien(message, user_id, response)
            elif intent == "search_parrain":
                response = await self._handle_search_parrain(message, user_id, response)
            elif intent == "ask_for_parrain":
                response = await self._handle_ask_for_parrain(message, user_id, response)
            elif intent == "find_skill_swap":
                response = await self._handle_find_skill_swap(message, user_id, response)
            else:
                response["message"] = self.responses["unknown"]
            
            return response
            
        except Exception as e:
            return {
                "intent": "error",
                "confidence": 0,
                "message": f"Une erreur s'est produite : {str(e)}",
                "data": None
            }
    
    async def _handle_find_groups(self, message: str, user_id: int, response: Dict) -> Dict:
        try:
            keywords = self.extract_keywords(message)
            centre_interet = keywords[0] if keywords else None
            
            groups = await self.db_queries.find_groups(user_id, centre_interet)
            
            if groups:
                response["message"] = self.responses["find_groups"]["success"]
                response["data"] = groups
            else:
                response["message"] = self.responses["find_groups"]["no_results"]
                response["data"] = []
                
        except Exception as e:
            response["message"] = self.responses["find_groups"]["error"]
            response["data"] = []
            
        return response
    
    async def _handle_demande_soutien(self, message: str, user_id: int, response: Dict) -> Dict:
        try:
            keywords = self.extract_keywords(message)
            
            if not keywords:
                response["message"] = self.responses["demande_soutien"]["missing_competence"]
                response["data"] = await self.db_queries.get_competences()
                return response
            
            competence_name = keywords[0]
            result = await self.db_queries.create_demande_soutien(user_id, competence_name)
            
            if "error" in result:
                response["message"] = f"{self.responses['demande_soutien']['error']} {result['error']}"
                response["data"] = None
            else:
                response["message"] = self.responses["demande_soutien"]["success"]
                response["data"] = result
                
        except Exception as e:
            response["message"] = self.responses["demande_soutien"]["error"]
            response["data"] = None
            
        return response
    
    async def _handle_search_parrain(self, message: str, user_id: int, response: Dict) -> Dict:
        try:
            user_info = await self.db_queries.get_user_info(user_id)
            filiere = user_info.get("filiere") if user_info else None
            
            parrains = await self.db_queries.find_parrains(user_id, filiere)
            
            if parrains:
                response["message"] = self.responses["search_parrain"]["success"]
                response["data"] = parrains
            else:
                response["message"] = self.responses["search_parrain"]["no_results"]
                response["data"] = []
                
        except Exception as e:
            response["message"] = self.responses["search_parrain"]["error"]
            response["data"] = []
            
        return response
    
    async def _handle_ask_for_parrain(self, message: str, user_id: int, response: Dict) -> Dict:
        try:
            numbers = self.extract_numbers(message)
            
            if not numbers:
                response["message"] = self.responses["ask_for_parrain"]["missing_parrain"]
                parrains = await self.db_queries.find_parrains(user_id)
                response["data"] = parrains
                return response
            
            parrain_id = numbers[0]
            result = await self.db_queries.create_parrain_request(user_id, parrain_id)
            
            if "error" in result:
                response["message"] = f"{self.responses['ask_for_parrain']['error']} {result['error']}"
                response["data"] = None
            else:
                response["message"] = self.responses["ask_for_parrain"]["success"]
                response["data"] = result
                
        except Exception as e:
            response["message"] = self.responses["ask_for_parrain"]["error"]
            response["data"] = None
            
        return response
    
    async def _handle_find_skill_swap(self, message: str, user_id: int, response: Dict) -> Dict:
        try:
            # Find skill swap partners using the recommendation service
            partners = await self.db_queries.find_skill_swap_partners(user_id, limit=5)
            
            if partners:
                response["message"] = self.responses["find_skill_swap"]["success"]
                response["data"] = partners
            else:
                response["message"] = self.responses["find_skill_swap"]["no_results"]
                response["data"] = []
                
        except Exception as e:
            response["message"] = self.responses["find_skill_swap"]["error"]
            response["data"] = []
            print(f"Error in _handle_find_skill_swap: {e}")
            
        return response
    
    async def get_suggestions(self, user_id: int) -> List[str]:
        try:
            user_info = await self.db_queries.get_user_info(user_id)
            suggestions = [
                "Montrez-moi les groupes disponibles",
                "J'ai besoin d'aide en programmation",
                "Je cherche un parrain",
                "Je veux échanger mes compétences"
            ]
            
            if user_info and "mentor" in user_info.get("roles", []):
                suggestions.append("Je veux aider comme parrain")
            
            return suggestions
            
        except Exception as e:
            return [
                "Montrez-moi les groupes disponibles",
                "J'ai besoin d'aide",
                "Je cherche un parrain",
                "Je veux échanger mes compétences"
            ]