from sentence_transformers import SentenceTransformer
from transformers import pipeline
import numpy as np
from typing import List, Dict, Tuple
import pickle
import os

class StudentMatcher:
    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), 'ai_models')
        self.sentence_model = None
        self.toxicity_classifier = None
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained models"""
        try:
            # Load sentence transformer for semantic similarity
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Load toxicity detection model
            self.toxicity_classifier = pipeline(
                "text-classification",
                model="unitary/toxic-bert",
                device=-1  # Use CPU
            )
        except Exception as e:
            print(f"Error loading models: {e}")
    
    def encode_profile(self, user_data: Dict) -> np.ndarray:
        """Encode user profile into vector representation"""
        if not self.sentence_model:
            return np.array([])
        
        # Combine user information into text
        profile_text = f"{user_data.get('nom', '')} {user_data.get('prenom', '')} "
        
        # Add roles if available
        if 'roles' in user_data and user_data['roles']:
            roles_text = " ".join([role.value if hasattr(role, 'value') else str(role) for role in user_data['roles']])
            profile_text += f"Roles: {roles_text} "
        
        # Add filiere and niveau
        if 'filiere' in user_data and user_data['filiere']:
            filiere = user_data['filiere'].value if hasattr(user_data['filiere'], 'value') else str(user_data['filiere'])
            profile_text += f"Program: {filiere} "
        
        if 'niveau' in user_data and user_data['niveau']:
            niveau = user_data['niveau'].value if hasattr(user_data['niveau'], 'value') else str(user_data['niveau'])
            profile_text += f"Year: {niveau} "
        
        # Add interests if available
        if 'interests' in user_data:
            interests_text = " ".join(user_data['interests'])
            profile_text += f"Interests: {interests_text} "
        
        # Add competencies if available
        if 'competences' in user_data:
            comp_text = " ".join([comp['nom'] for comp in user_data['competences']])
            profile_text += f"Skills: {comp_text}"
        
        return self.sentence_model.encode(profile_text)
    
    def find_matches(self, user_vector: np.ndarray, candidate_vectors: List[np.ndarray], 
                    top_k: int = 5) -> List[Tuple[int, float]]:
        """Find top k similar users based on vector similarity"""
        if len(candidate_vectors) == 0:
            return []
        
        # Calculate cosine similarities
        similarities = []
        for i, candidate_vector in enumerate(candidate_vectors):
            if candidate_vector.size == 0:
                continue
            similarity = np.dot(user_vector, candidate_vector) / (
                np.linalg.norm(user_vector) * np.linalg.norm(candidate_vector)
            )
            similarities.append((i, similarity))
        
        # Sort by similarity and return top k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def is_toxic_content(self, text: str) -> bool:
        """Check if text contains toxic content"""
        if not self.toxicity_classifier:
            return False
        
        try:
            result = self.toxicity_classifier(text)
            # Return True if toxic label has high confidence
            for item in result:
                print(f"Label: {item['label']}, Score: {item['score']}")
                if item['label'].lower() == 'toxic' and float(item['score']) > 0.7:
                    print("Toxic content detected")
                    return True
            return False
        except Exception as e:
            print(f"Error in toxicity detection: {e}")
            return False
    
    def match_students_by_interests(self, target_interests: List[str], 
                                  candidate_interests: List[List[str]]) -> List[Tuple[int, float]]:
        """Match students based on shared interests"""
        scores = []
        target_set = set(target_interests)
        
        for i, candidate_int in enumerate(candidate_interests):
            candidate_set = set(candidate_int)
            # Calculate Jaccard similarity
            intersection = len(target_set & candidate_set)
            union = len(target_set | candidate_set)
            score = intersection / union if union > 0 else 0
            scores.append((i, score))
        
        return sorted(scores, key=lambda x: x[1], reverse=True)
    
    def match_by_filiere_niveau(self, target_filiere: str, target_niveau: int,
                               candidates: List[Dict]) -> List[Tuple[int, float]]:
        """Match students by same filiere and similar niveau"""
        scores = []
        
        for i, candidate in enumerate(candidates):
            score = 0.0
            
            # Same filiere gets high score
            candidate_filiere = candidate.get('filiere')
            if candidate_filiere:
                filiere_val = candidate_filiere.value if hasattr(candidate_filiere, 'value') else str(candidate_filiere)
                if filiere_val == target_filiere:
                    score += 0.6
            
            # Similar niveau gets additional score
            candidate_niveau = candidate.get('niveau')
            if candidate_niveau:
                niveau_val = candidate_niveau.value if hasattr(candidate_niveau, 'value') else int(candidate_niveau)
                niveau_diff = abs(niveau_val - target_niveau)
                if niveau_diff == 0:
                    score += 0.4
                elif niveau_diff == 1:
                    score += 0.2
                elif niveau_diff == 2:
                    score += 0.1
            
            scores.append((i, score))
        
        return sorted(scores, key=lambda x: x[1], reverse=True)
    
    def recommend_mentors(self, student_competences: List[str], 
                         mentor_competences: List[List[str]]) -> List[Tuple[int, float]]:
        """Recommend mentors based on competency gaps"""
        scores = []
        student_comp_set = set(student_competences)
        
        for i, mentor_comp in enumerate(mentor_competences):
            mentor_comp_set = set(mentor_comp)
            # Score based on how many skills mentor has that student lacks
            missing_skills = mentor_comp_set - student_comp_set
            score = len(missing_skills) / len(mentor_comp_set) if mentor_comp_set else 0
            scores.append((i, score))
        
        return sorted(scores, key=lambda x: x[1], reverse=True)
    
    def find_cross_filiere_collaborators(self, user_filiere: str, user_niveau: int,
                                       candidates: List[Dict]) -> List[Tuple[int, float]]:
        """Find collaborators from different filieres but similar niveau for interdisciplinary projects"""
        scores = []
        
        for i, candidate in enumerate(candidates):
            score = 0.0
            
            # Different filiere gets points (for diversity)
            candidate_filiere = candidate.get('filiere')
            if candidate_filiere:
                filiere_val = candidate_filiere.value if hasattr(candidate_filiere, 'value') else str(candidate_filiere)
                if filiere_val != user_filiere:
                    score += 0.5
            
            # Similar niveau is important for peer collaboration
            candidate_niveau = candidate.get('niveau')
            if candidate_niveau:
                niveau_val = candidate_niveau.value if hasattr(candidate_niveau, 'value') else int(candidate_niveau)
                niveau_diff = abs(niveau_val - user_niveau)
                if niveau_diff == 0:
                    score += 0.5
                elif niveau_diff == 1:
                    score += 0.3
            
            scores.append((i, score))
        
        return sorted(scores, key=lambda x: x[1], reverse=True)