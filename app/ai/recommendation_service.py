from typing import List, Dict, Optional
import numpy as np
from .student_matcher import StudentMatcher
from ..models.models import Utilisateur, CentreInteret, Competence, UtilisateurCentreInteret, UtilisateurCompetence

class RecommendationService:
    def __init__(self):
        self.matcher = StudentMatcher()
        self.user_vectors_cache = {}
    
    async def get_user_profile_data(self, user_id: int) -> Dict:
        """Get complete user profile data including interests and competencies"""
        user = await Utilisateur.get(id=user_id)
        
        # Get user interests
        user_interests = await UtilisateurCentreInteret.filter(
            utilisateur_id=user_id
        ).prefetch_related('centreInteret')
        interests = [ui.centreInteret.titre for ui in user_interests]
        
        # Get user competencies
        user_competences = await UtilisateurCompetence.filter(
            utilisateur_id=user_id
        ).prefetch_related('competence')
        competences = [{'nom': uc.competence.nom, 'niveau': uc.niveau} for uc in user_competences]
        
        return {
            'id': user.id,
            'nom': user.nom,
            'prenom': user.prenom,
            'role': user.role,
            'score': user.score,
            'interests': interests,
            'competences': competences
        }
    
    async def find_study_buddies(self, user_id: int, limit: int = 5) -> List[Dict]:
        """Find study buddies with similar interests"""
        user_profile = await self.get_user_profile_data(user_id)
        
        # Get all other users with similar role (students)
        candidates = await Utilisateur.filter(role='student').exclude(id=user_id)
        
        candidate_profiles = []
        for candidate in candidates:
            profile = await self.get_user_profile_data(candidate.id)
            candidate_profiles.append(profile)
        
        # Use interest-based matching
        candidate_interests = [profile['interests'] for profile in candidate_profiles]
        matches = self.matcher.match_students_by_interests(
            user_profile['interests'], 
            candidate_interests
        )
        
        # Return top matches with user data
        results = []
        for idx, score in matches[:limit]:
            if score > 0:  # Only return matches with some similarity
                candidate = candidate_profiles[idx]
                candidate['similarity_score'] = score
                results.append(candidate)
        
        return results
    
    async def find_mentors(self, student_id: int, limit: int = 5) -> List[Dict]:
        """Find potential mentors based on competency gaps"""
        student_profile = await self.get_user_profile_data(student_id)
        student_competences = [comp['nom'] for comp in student_profile['competences']]
        
        # Get all mentors/teachers
        mentors = await Utilisateur.filter(role__in=['teacher', 'mentor'])
        
        mentor_profiles = []
        mentor_competences = []
        for mentor in mentors:
            profile = await self.get_user_profile_data(mentor.id)
            mentor_profiles.append(profile)
            mentor_competences.append([comp['nom'] for comp in profile['competences']])
        
        # Find mentors with complementary skills
        matches = self.matcher.recommend_mentors(student_competences, mentor_competences)
        
        results = []
        for idx, score in matches[:limit]:
            if score > 0:
                mentor = mentor_profiles[idx]
                mentor['match_score'] = score
                results.append(mentor)
        
        return results
    
    async def get_semantic_matches(self, user_id: int, limit: int = 5) -> List[Dict]:
        """Find matches using semantic similarity of profiles"""
        user_profile = await self.get_user_profile_data(user_id)
        user_vector = self.matcher.encode_profile(user_profile)
        
        if user_vector.size == 0:
            return []
        
        # Get all other users
        candidates = await Utilisateur.all().exclude(id=user_id)
        
        candidate_profiles = []
        candidate_vectors = []
        
        for candidate in candidates:
            profile = await self.get_user_profile_data(candidate.id)
            vector = self.matcher.encode_profile(profile)
            if vector.size > 0:
                candidate_profiles.append(profile)
                candidate_vectors.append(vector)
        
        # Find semantic matches
        matches = self.matcher.find_matches(user_vector, candidate_vectors, limit)
        
        results = []
        for idx, score in matches:
            if score > 0.3:  # Minimum similarity threshold
                candidate = candidate_profiles[idx]
                candidate['semantic_score'] = score
                results.append(candidate)
        
        return results
    
    async def check_content_safety(self, text: str) -> bool:
        """Check if content is safe (non-toxic)"""
        return not self.matcher.is_toxic_content(text)
    
    async def get_group_recommendations(self, user_id: int, limit: int = 5) -> List[Dict]:
        """Recommend groups based on user interests"""
        user_profile = await self.get_user_profile_data(user_id)
        user_interests = set(user_profile['interests'])
        
        # Get all groups with their center of interest
        from ..models.models import Groupe
        groups = await Groupe.all().prefetch_related('centreInteret')
        
        # Score groups based on interest match
        group_scores = []
        for group in groups:
            group_interest = group.centreInteret.titre
            score = 1.0 if group_interest in user_interests else 0.0
            
            if score > 0:
                group_scores.append({
                    'id': group.id,
                    'nom': group.nom,
                    'description': group.description,
                    'interest': group_interest,
                    'match_score': score
                })
        
        # Sort by score and return top matches
        group_scores.sort(key=lambda x: x['match_score'], reverse=True)
        return group_scores[:limit]