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
    
    async def skill_swap(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Recommends users who have skills that the current user lacks or needs improvement in.
        
        Args:
            user_id: ID of the current user
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommended users with skill swap scores and explanations
        """
        user_profile = await self.get_user_profile_data(user_id)
        
        # Get all other users excluding the current user
        all_users = await Utilisateur.all().exclude(id=user_id)
        
        if not all_users:
            return []
        
        # Get profiles for all candidates
        candidate_profiles = []
        for user in all_users:
            profile = await self.get_user_profile_data(user.id)
            candidate_profiles.append(profile)
        
        try:
            # Get user's current skills and levels
            user_competences = user_profile.get('competences', [])
            user_skills = {}
            
            # Map user's skills to their levels (convert to numeric for comparison)
            for comp in user_competences:
                skill_name = comp.get('nom', '').lower()
                skill_level = self._normalize_skill_level(comp.get('niveau', ''))
                user_skills[skill_name] = skill_level
            
            recommendations = []
            
            for candidate in candidate_profiles:
                candidate_competences = candidate.get('competences', [])
                if not candidate_competences:
                    continue
                
                # Calculate skill swap score for this candidate
                swap_score, swap_details = self._calculate_swap_score(
                    user_skills, candidate_competences, user_profile, candidate
                )
                
                if swap_score > 0:
                    recommendations.append({
                        **candidate,
                        'swap_score': swap_score,
                        'swap_details': swap_details,
                        'recommendation_type': 'skill_swap'
                    })
            
            # Sort by swap score and return top recommendations
            recommendations.sort(key=lambda x: x['swap_score'], reverse=True)
            return recommendations[:limit]
            
        except Exception as e:
            print(f"Error in skill swap recommendation: {e}")
            return []
    
    def _calculate_swap_score(self, user_skills: Dict[str, int], 
                            candidate_competences: List[Dict],
                            user_profile: Dict, candidate_profile: Dict) -> tuple:
        """
        Calculate how valuable a skill swap would be between two users
        
        Returns:
            Tuple of (swap_score, swap_details)
        """
        score = 0.0
        swap_details = {
            'skills_they_offer': [],
            'skills_you_offer': [],
            'mutual_benefits': [],
            'skill_gaps_filled': 0,
            'complementary_skills': 0
        }
        
        # Get candidate's skills
        candidate_skills = {}
        for comp in candidate_competences:
            skill_name = comp.get('nom', '').lower()
            skill_level = self._normalize_skill_level(comp.get('niveau', ''))
            candidate_skills[skill_name] = skill_level
        
        # Check what skills the candidate has that user lacks or needs improvement in
        for skill, candidate_level in candidate_skills.items():
            user_level = user_skills.get(skill, 0)
            
            # If user doesn't have this skill or has lower level
            if user_level == 0:
                # User completely lacks this skill
                score += 2.0 * (candidate_level / 5.0)  # Higher weight for missing skills
                swap_details['skills_they_offer'].append({
                    'skill': skill,
                    'their_level': candidate_level,
                    'your_level': 0,
                    'benefit': 'New skill to learn'
                })
                swap_details['skill_gaps_filled'] += 1
                
            elif candidate_level > user_level:
                # User has skill but at lower level
                improvement_potential = candidate_level - user_level
                score += 1.0 * (improvement_potential / 5.0)
                swap_details['skills_they_offer'].append({
                    'skill': skill,
                    'their_level': candidate_level,
                    'your_level': user_level,
                    'benefit': f'Improve from level {user_level} to {candidate_level}'
                })
        
        # Check what skills user has that candidate lacks (mutual benefit)
        for skill, user_level in user_skills.items():
            candidate_level = candidate_skills.get(skill, 0)
            
            if candidate_level == 0 and user_level > 2:  # Only if user is competent
                score += 0.5 * (user_level / 5.0)  # Bonus for mutual benefit
                swap_details['skills_you_offer'].append({
                    'skill': skill,
                    'your_level': user_level,
                    'their_level': 0,
                    'benefit': 'You can teach this skill'
                })
                
            elif user_level > candidate_level and user_level > 2:
                improvement_potential = user_level - candidate_level
                score += 0.3 * (improvement_potential / 5.0)
                swap_details['skills_you_offer'].append({
                    'skill': skill,
                    'your_level': user_level,
                    'their_level': candidate_level,
                    'benefit': f'You can help improve from level {candidate_level} to {user_level}'
                })
        
        # Bonus for complementary skills (different domains)
        user_filiere = user_profile.get('filiere')
        candidate_filiere = candidate_profile.get('filiere')
        
        if user_filiere and candidate_filiere and user_filiere != candidate_filiere:
            score += 0.5  # Cross-domain collaboration bonus
            swap_details['complementary_skills'] = 1
            swap_details['mutual_benefits'].append(
                f"Cross-domain collaboration between {user_filiere} and {candidate_filiere}"
            )
        
        # Bonus for similar academic level (easier collaboration)
        user_niveau = user_profile.get('niveau')
        candidate_niveau = candidate_profile.get('niveau')
        
        if user_niveau and candidate_niveau:
            level_diff = abs(user_niveau - candidate_niveau)
            if level_diff <= 1:  # Same or adjacent levels
                score += 0.3
                swap_details['mutual_benefits'].append("Similar academic level for effective collaboration")
        
        return score, swap_details
    
    def _normalize_skill_level(self, level: str) -> int:
        """
        Convert skill level string to numeric value (1-5 scale)
        """
        if not level:
            return 0
        
        level_str = str(level).lower()
        
        # Map common skill level terms to numbers
        level_mapping = {
            'débutant': 1, 'beginner': 1, 'novice': 1, '1': 1,
            'intermédiaire': 2, 'intermediate': 2, '2': 2,
            'avancé': 3, 'advanced': 3, '3': 3,
            'expert': 4, '4': 4,
            'maître': 5, 'master': 5, '5': 5
        }
        
        for key, value in level_mapping.items():
            if key in level_str:
                return value
        
        # Try to extract number directly
        try:
            num = int(''.join(filter(str.isdigit, level_str)))
            return min(max(num, 1), 5)  # Clamp between 1 and 5
        except (ValueError, TypeError):
            return 1  # Default to beginner if can't parse