from typing import List, Dict, Optional
from .recommendation_service import RecommendationService
from ..models.models import RoleEnum
import numpy as np
class AIService:
    """
    Main AI service that provides intelligent recommendations for student connections
    """
    
    def __init__(self):
        self.recommendation_service = RecommendationService()
    
    async def get_smart_recommendations(self, user_id: int, recommendation_type: str = "all", limit: int = 10) -> Dict:
        """
        Get comprehensive recommendations based on user profile and preferences
        
        Args:
            user_id: ID of the user requesting recommendations
            recommendation_type: Type of recommendations ('study_buddies', 'mentors', 'collaborators', 'all')
            limit: Maximum number of recommendations per category
        
        Returns:
            Dictionary with different types of recommendations
        """
        user_profile = await self.recommendation_service.get_user_profile_data(user_id)
        user_roles = [role.value if hasattr(role, 'value') else str(role) for role in user_profile.get('roles', [])]
        
        recommendations = {
            'user_profile': {
                'id': user_profile['id'],
                'name': f"{user_profile['nom']} {user_profile['prenom']}",
                'roles': user_roles,
                'filiere': user_profile['filiere'].value if user_profile.get('filiere') else None,
                'niveau': user_profile['niveau'].value if user_profile.get('niveau') else None,
                'interests_count': len(user_profile.get('interests', [])),
                'competences_count': len(user_profile.get('competences', []))
            }
        }
        
        # Study buddies - for students
        if recommendation_type in ['study_buddies', 'all'] and RoleEnum.STUDENT.value in user_roles:
            study_buddies = await self.recommendation_service.find_study_buddies(user_id, limit//2)
            recommendations['study_buddies'] = {
                'count': len(study_buddies),
                'recommendations': study_buddies
            }
        
        # Mentors - for students
        if recommendation_type in ['mentors', 'all'] and RoleEnum.STUDENT.value in user_roles:
            mentors = await self.recommendation_service.find_mentors(user_id, limit//3)
            recommendations['mentors'] = {
                'count': len(mentors),
                'recommendations': mentors
            }
        
        # Interdisciplinary collaborators
        if recommendation_type in ['collaborators', 'all']:
            collaborators = await self.recommendation_service.find_interdisciplinary_collaborators(user_id, limit//3)
            recommendations['interdisciplinary_collaborators'] = {
                'count': len(collaborators),
                'recommendations': collaborators
            }
        
        # Semantic matches (people with similar overall profiles)
        if recommendation_type in ['semantic', 'all']:
            semantic_matches = await self.recommendation_service.get_semantic_matches(user_id, limit//4)
            recommendations['semantic_matches'] = {
                'count': len(semantic_matches),
                'recommendations': semantic_matches
            }
        
        # Group recommendations
        if recommendation_type in ['groups', 'all']:
            group_recommendations = await self.recommendation_service.get_group_recommendations(user_id, limit//2)
            recommendations['recommended_groups'] = {
                'count': len(group_recommendations),
                'recommendations': group_recommendations
            }
        
        return recommendations
    
    async def analyze_user_compatibility(self, user1_id: int, user2_id: int) -> Dict:
        """
        Analyze compatibility between two users for collaboration/mentorship
        
        Args:
            user1_id: First user ID
            user2_id: Second user ID
            
        Returns:
            Compatibility analysis with scores and recommendations
        """
        user1_profile = await self.recommendation_service.get_user_profile_data(user1_id)
        user2_profile = await self.recommendation_service.get_user_profile_data(user2_id)
        
        # Encode profiles for semantic similarity
        user1_vector = self.recommendation_service.matcher.encode_profile(user1_profile)
        user2_vector = self.recommendation_service.matcher.encode_profile(user2_profile)
        
        compatibility_score = 0.0
        compatibility_factors = []
        
        # Semantic similarity
        if user1_vector.size > 0 and user2_vector.size > 0:
            semantic_similarity = np.dot(user1_vector, user2_vector) / (
                np.linalg.norm(user1_vector) * np.linalg.norm(user2_vector)
            )
            compatibility_score += semantic_similarity * 0.3
            compatibility_factors.append({
                'factor': 'semantic_similarity',
                'score': float(semantic_similarity),
                'weight': 0.3
            })
        
        # Interest overlap
        user1_interests = set(user1_profile.get('interests', []))
        user2_interests = set(user2_profile.get('interests', []))
        if user1_interests or user2_interests:
            interest_overlap = len(user1_interests & user2_interests) / len(user1_interests | user2_interests) if (user1_interests | user2_interests) else 0
            compatibility_score += interest_overlap * 0.25
            compatibility_factors.append({
                'factor': 'shared_interests',
                'score': interest_overlap,
                'weight': 0.25,
                'shared_interests': list(user1_interests & user2_interests)
            })
        
        # Academic compatibility
        academic_score = 0.0
        if user1_profile.get('filiere') and user2_profile.get('filiere'):
            filiere1 = user1_profile['filiere'].value if hasattr(user1_profile['filiere'], 'value') else str(user1_profile['filiere'])
            filiere2 = user2_profile['filiere'].value if hasattr(user2_profile['filiere'], 'value') else str(user2_profile['filiere'])
            
            if filiere1 == filiere2:
                academic_score += 0.6  # Same program
            else:
                academic_score += 0.3  # Different programs can be good for diversity
        
        if user1_profile.get('niveau') and user2_profile.get('niveau'):
            niveau1 = user1_profile['niveau'].value if hasattr(user1_profile['niveau'], 'value') else int(user1_profile['niveau'])
            niveau2 = user2_profile['niveau'].value if hasattr(user2_profile['niveau'], 'value') else int(user2_profile['niveau'])
            
            niveau_diff = abs(niveau1 - niveau2)
            if niveau_diff == 0:
                academic_score += 0.4  # Same level
            elif niveau_diff == 1:
                academic_score += 0.3  # Close levels
            elif niveau_diff == 2:
                academic_score += 0.1  # Moderate difference
        
        compatibility_score += academic_score * 0.2
        compatibility_factors.append({
            'factor': 'academic_compatibility',
            'score': academic_score,
            'weight': 0.2
        })
        
        # Role compatibility
        user1_roles = set([role.value if hasattr(role, 'value') else str(role) for role in user1_profile.get('roles', [])])
        user2_roles = set([role.value if hasattr(role, 'value') else str(role) for role in user2_profile.get('roles', [])])
        
        role_compatibility = 0.0
        if RoleEnum.STUDENT.value in user1_roles and RoleEnum.MENTOR.value in user2_roles:
            role_compatibility = 0.9  # Perfect mentor-student match
        elif RoleEnum.STUDENT.value in user2_roles and RoleEnum.MENTOR.value in user1_roles:
            role_compatibility = 0.9  # Perfect mentor-student match
        elif RoleEnum.STUDENT.value in user1_roles and RoleEnum.STUDENT.value in user2_roles:
            role_compatibility = 0.7  # Good peer match
        else:
            role_compatibility = 0.5  # Other combinations
        
        compatibility_score += role_compatibility * 0.25
        compatibility_factors.append({
            'factor': 'role_compatibility',
            'score': role_compatibility,
            'weight': 0.25
        })
        
        # Generate recommendations based on compatibility
        recommendations = []
        if compatibility_score > 0.7:
            recommendations.append("Highly compatible - excellent match for collaboration")
        elif compatibility_score > 0.5:
            recommendations.append("Good compatibility - worth connecting")
        elif compatibility_score > 0.3:
            recommendations.append("Moderate compatibility - potential for specific projects")
        else:
            recommendations.append("Low compatibility - may not be the best match")
        
        return {
            'compatibility_score': float(compatibility_score),
            'compatibility_level': 'high' if compatibility_score > 0.7 else 'medium' if compatibility_score > 0.4 else 'low',
            'factors': compatibility_factors,
            'recommendations': recommendations,
            'users': {
                'user1': {
                    'id': user1_profile['id'],
                    'name': f"{user1_profile['nom']} {user1_profile['prenom']}",
                    'roles': list(user1_roles),
                    'filiere': user1_profile['filiere'].value if user1_profile.get('filiere') else None,
                    'niveau': user1_profile['niveau'].value if user1_profile.get('niveau') else None
                },
                'user2': {
                    'id': user2_profile['id'],
                    'name': f"{user2_profile['nom']} {user2_profile['prenom']}",
                    'roles': list(user2_roles),
                    'filiere': user2_profile['filiere'].value if user2_profile.get('filiere') else None,
                    'niveau': user2_profile['niveau'].value if user2_profile.get('niveau') else None
                }
            }
        }
    
    async def moderate_content(self, text: str) -> Dict:
        """
        Check content for toxicity and provide moderation recommendations
        
        Args:
            text: Text content to moderate
            
        Returns:
            Moderation result with toxicity score and recommendations
        """
        is_toxic = await self.recommendation_service.check_content_safety(text)
        
        return {
            'is_safe': not is_toxic,
            'is_toxic': is_toxic,
            'confidence': 'high' if is_toxic else 'medium',
            'action': 'block' if is_toxic else 'approve',
            'message': 'Content appears to contain toxic language and should be reviewed' if is_toxic else 'Content appears safe'
        }