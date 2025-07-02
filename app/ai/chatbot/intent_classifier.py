from sentence_transformers import SentenceTransformer
import numpy as np
from typing import Dict, List, Tuple
import json
from sklearn.metrics.pairwise import cosine_similarity

class IntentClassifier:
    def __init__(self, model_path: str = None):
        if model_path is None:
            # Try to load from local models directory first
            import os
            local_model_path = os.path.join(os.path.dirname(__file__), '..', 'ai_models', 'multilingual-chatbot')
            if os.path.exists(local_model_path):
                self.model = SentenceTransformer(local_model_path)
            else:
                # Fallback to downloading from HuggingFace
                self.model = SentenceTransformer("all-mpnet-base-v2")
        else:
            self.model = SentenceTransformer(model_path)
        self.intents = {
            "find_groups": [
                "Je veux trouver des groupes",
                "Chercher des groupes",
                "Où sont les groupes?",
                "Montrez-moi les groupes",
                "Je cherche un groupe",
                "Groupes disponibles",
                "Voir les groupes",
                "Lister les groupes"
            ],
            "demande_soutien": [
                "J'ai besoin d'aide",
                "Je demande de l'aide",
                "Pouvez-vous m'aider?",
                "J'ai besoin de soutien",
                "Je cherche de l'assistance",
                "J'ai un problème",
                "Je suis bloqué",
                "Aide moi s'il te plaît"
            ],
            "search_parrain": [
                "Je cherche un parrain",
                "Où trouver un mentor?",
                "J'ai besoin d'un parrain",
                "Trouver un mentor",
                "Chercher un parrain",
                "Qui peut être mon parrain?",
                "Je veux un mentor",
                "Parrain disponible"
            ],
            "ask_for_parrain": [
                "Je veux devenir parrain",
                "Comment être mentor?",
                "Je peux aider comme parrain",
                "Proposer mes services de parrain",
                "Être mentor",
                "Devenir parrain",
                "Offrir mon aide comme mentor",
                "Je veux mentorer"
            ]
        }
        
        self.intent_embeddings = {}
        self._compute_intent_embeddings()
    
    def _compute_intent_embeddings(self):
        for intent, examples in self.intents.items():
            embeddings = self.model.encode(examples)
            self.intent_embeddings[intent] = np.mean(embeddings, axis=0)
    
    def classify_intent(self, text: str, threshold: float = 0.5) -> Tuple[str, float]:
        text_embedding = self.model.encode([text])
        
        best_intent = None
        best_score = 0
        
        for intent, intent_embedding in self.intent_embeddings.items():
            similarity = cosine_similarity(text_embedding, [intent_embedding])[0][0]
            
            if similarity > best_score:
                best_score = similarity
                best_intent = intent
        
        if best_score >= threshold:
            return best_intent, best_score
        else:
            return "unknown", best_score