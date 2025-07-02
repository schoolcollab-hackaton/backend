from typing import List, Dict, Optional
import numpy as np
from .student_matcher import StudentMatcher
from ..models.models import (
    Utilisateur, CentreInteret, Competence, UtilisateurCentreInteret, 
    UtilisateurCompetence, UtilisateurRole, RoleEnum
)

class RecommendationService:
    def __init__(self):
        self.matcher = StudentMatcher()
        self.user_vectors_cache = {}
    
    async def get_user_profile_data(self, user_id: int) -> Dict:
        """Get complete user profile data including interests, competencies, and roles"""
        user = await Utilisateur.get(id=user_id)
        
        # Get user roles
        user_roles = await UtilisateurRole.filter(
            utilisateur_id=user_id, statut='active'
        )
        roles = [ur.role for ur in user_roles]
        
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
            'roles': roles,
            'score': user.score,
            'filiere': user.filiere,
            'niveau': user.niveau,
            'interests': interests,
            'competences': competences
        }
    
    async def find_study_buddies(self, user_id: int, limit: int = 5) -> List[Dict]:
        """Find study buddies with similar interests and academic level"""
        user_profile = await self.get_user_profile_data(user_id)
        
        # Get all other users who have student role
        student_role_users = await UtilisateurRole.filter(
            role=RoleEnum.STUDENT, statut='active'
        ).exclude(utilisateur_id=user_id)
        
        candidate_profiles = []
        for ur in student_role_users:
            profile = await self.get_user_profile_data(ur.utilisateur_id)
            candidate_profiles.append(profile)
        
        # Combine different matching strategies
        results = []
        
        # 1. Same filiere and niveau matching
        if user_profile.get('filiere') and user_profile.get('niveau'):
            filiere_val = user_profile['filiere'].value if hasattr(user_profile['filiere'], 'value') else str(user_profile['filiere'])
            niveau_val = user_profile['niveau'].value if hasattr(user_profile['niveau'], 'value') else int(user_profile['niveau'])
            
            filiere_matches = self.matcher.match_by_filiere_niveau(
                filiere_val, niveau_val, candidate_profiles
            )
            
            for idx, score in filiere_matches[:limit//2]:
                if score > 0.3:
                    candidate = candidate_profiles[idx].copy()
                    candidate['match_type'] = 'same_program'
                    candidate['similarity_score'] = score
                    results.append(candidate)
        
        # 2. Interest-based matching for remaining slots
        remaining_slots = limit - len(results)
        if remaining_slots > 0:
            candidate_interests = [profile['interests'] for profile in candidate_profiles]
            interest_matches = self.matcher.match_students_by_interests(
                user_profile['interests'], 
                candidate_interests
            )
            
            for idx, score in interest_matches[:remaining_slots]:
                if score > 0.1 and candidate_profiles[idx] not in [r for r in results]:
                    candidate = candidate_profiles[idx].copy()
                    candidate['match_type'] = 'shared_interests'
                    candidate['similarity_score'] = score
                    results.append(candidate)
        
        return results[:limit]
    
    async def find_mentors(self, student_id: int, limit: int = 5) -> List[Dict]:
        """Find potential mentors based on competency gaps and academic progression"""
        student_profile = await self.get_user_profile_data(student_id)
        student_competences = [comp['nom'] for comp in student_profile['competences']]
        
        # Get all users with mentor or teacher roles
        mentor_role_users = await UtilisateurRole.filter(
            role__in=[RoleEnum.MENTOR, RoleEnum.TEACHER], statut='active'
        )
        
        mentor_profiles = []
        mentor_competences = []
        for ur in mentor_role_users:
            profile = await self.get_user_profile_data(ur.utilisateur_id)
            mentor_profiles.append(profile)
            mentor_competences.append([comp['nom'] for comp in profile['competences']])
        
        # Find mentors with complementary skills
        matches = self.matcher.recommend_mentors(student_competences, mentor_competences)
        
        results = []
        for idx, score in matches[:limit]:
            if score > 0:
                mentor = mentor_profiles[idx].copy()
                mentor['match_score'] = score
                mentor['match_type'] = 'skill_complementarity'
                
                # Bonus for mentors in same filiere but higher niveau
                if (student_profile.get('filiere') and mentor.get('filiere') and 
                    student_profile.get('niveau') and mentor.get('niveau')):
                    
                    student_filiere = student_profile['filiere'].value if hasattr(student_profile['filiere'], 'value') else str(student_profile['filiere'])
                    mentor_filiere = mentor['filiere'].value if hasattr(mentor['filiere'], 'value') else str(mentor['filiere'])
                    student_niveau = student_profile['niveau'].value if hasattr(student_profile['niveau'], 'value') else int(student_profile['niveau'])
                    mentor_niveau = mentor['niveau'].value if hasattr(mentor['niveau'], 'value') else int(mentor['niveau'])
                    
                    if student_filiere == mentor_filiere and mentor_niveau > student_niveau:
                        mentor['match_score'] += 0.2
                        mentor['match_type'] = 'senior_same_program'
                
                results.append(mentor)
        
        # Sort by final score
        results.sort(key=lambda x: x['match_score'], reverse=True)
        return results[:limit]
    
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
                candidate = candidate_profiles[idx].copy()
                candidate['semantic_score'] = score
                candidate['match_type'] = 'semantic_similarity'
                results.append(candidate)
        
        return results
    
    async def find_interdisciplinary_collaborators(self, user_id: int, limit: int = 5) -> List[Dict]:
        """Find collaborators from different filieres for interdisciplinary projects"""
        user_profile = await self.get_user_profile_data(user_id)
        
        if not user_profile.get('filiere') or not user_profile.get('niveau'):
            return []
        
        # Get all students excluding same user
        student_role_users = await UtilisateurRole.filter(
            role=RoleEnum.STUDENT, statut='active'
        ).exclude(utilisateur_id=user_id)
        
        candidate_profiles = []
        for ur in student_role_users:
            profile = await self.get_user_profile_data(ur.utilisateur_id)
            candidate_profiles.append(profile)
        
        user_filiere = user_profile['filiere'].value if hasattr(user_profile['filiere'], 'value') else str(user_profile['filiere'])
        user_niveau = user_profile['niveau'].value if hasattr(user_profile['niveau'], 'value') else int(user_profile['niveau'])
        
        # Find cross-filiere collaborators
        matches = self.matcher.find_cross_filiere_collaborators(
            user_filiere, user_niveau, candidate_profiles
        )
        
        results = []
        for idx, score in matches[:limit]:
            if score > 0.3:
                candidate = candidate_profiles[idx].copy()
                candidate['collaboration_score'] = score
                candidate['match_type'] = 'interdisciplinary'
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