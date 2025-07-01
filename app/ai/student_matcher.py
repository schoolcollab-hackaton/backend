from sentence_transformers import SentenceTransformer
from transformers import pipeline
import numpy as np
from typing import List, Dict, Tuple
import pickle
import os

class StudentMatcher:
    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), 'models')
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
        profile_text += f"Role: {user_data.get('role', '')} "
        
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
                if item['label'] == 'TOXIC' and item['score'] > 0.7:
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