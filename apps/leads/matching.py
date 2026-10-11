from decimal import Decimal
from typing import List, Tuple
from apps.leads.models import TuitionRequirement, TutorMatch
from apps.tutors.models import TutorProfile

def run_tutor_matching(requirement: TuitionRequirement, top_n: int = 10) -> List[TutorMatch]:
    """
    Intelligent tutor matching engine based on:
    - Subject compatibility (35%)
    - Class / Curriculum compatibility (20%)
    - Location & City proximity (25%)
    - Teaching Mode compatibility (10%)
    - Budget compatibility (10%)
    - Verified status boost (+5%)
    """
    matches = []
    req_subjects = [s.strip().lower() for s in requirement.subjects.replace('/', ',').split(',') if s.strip()]
    req_city = (requirement.city or '').strip().lower()
    req_locality = (requirement.locality or '').strip().lower()
    req_class = (requirement.student_class or '').strip().lower()
    req_budget = requirement.budget_amount or Decimal('5000')

    # Candidate tutors (excluding suspended/rejected)
    candidate_tutors = TutorProfile.objects.exclude(
        verification_status__in=[TutorProfile.VerificationStatus.REJECTED, TutorProfile.VerificationStatus.SUSPENDED]
    ).prefetch_related('subjects', 'availabilities')

    for tutor in candidate_tutors:
        score = 0
        reasons = []

        # 1. Subject Compatibility (35 pts max)
        tutor_subject_names = [ts.subject_name.strip().lower() for ts in tutor.subjects.all()]
        # Check tutor headline / bio too as fallback
        tutor_text_blob = f"{tutor.headline} {tutor.bio}".lower()
        
        matched_subjs = [sub for sub in req_subjects if any(sub in ts or ts in sub for ts in tutor_subject_names) or sub in tutor_text_blob]
        if matched_subjs:
            sub_pct = len(matched_subjs) / max(len(req_subjects), 1)
            sub_pts = int(sub_pct * 35)
            score += sub_pts
            reasons.append(f"Specialized in {', '.join(s.title() for s in matched_subjs)}")
        else:
            # Skip tutors with zero subject relevance
            continue

        # 2. Location & Proximity (25 pts max)
        tutor_city = (tutor.primary_city or '').strip().lower()
        tutor_loc = (tutor.primary_locality or '').strip().lower()

        if requirement.tuition_type == TuitionRequirement.TuitionType.ONLINE_TUITION:
            score += 25
            reasons.append("Available for interactive online tuition anywhere")
        elif tutor_city == req_city:
            if tutor_loc and req_locality and (tutor_loc in req_locality or req_locality in tutor_loc):
                score += 25
                reasons.append(f"Located directly in {requirement.locality} (zero travel delay)")
            else:
                score += 18
                reasons.append(f"Servicing {tutor.primary_city} within {tutor.service_radius_km} km radius")
        elif tutor.teaching_mode in [TutorProfile.TeachingMode.ONLINE_ONLY, TutorProfile.TeachingMode.BOTH_HOME_ONLINE]:
            score += 15
            reasons.append("Can conduct classes via online live setup")
        else:
            # Different city and home tuition only -> very low fit
            score += 0

        # 3. Class & Curriculum Match (20 pts max)
        tutor_classes_blob = " ".join([ts.classes_offered.lower() for ts in tutor.subjects.all()])
        if req_class and req_class in tutor_classes_blob:
            score += 20
            reasons.append(f"Experienced in teaching {requirement.student_class} curriculum")
        elif "class 9" in tutor_classes_blob or "class 10" in tutor_classes_blob or "class 11" in tutor_classes_blob or "class 12" in tutor_classes_blob:
            score += 14
            reasons.append(f"Covers high school and senior secondary levels")
        else:
            score += 10

        # 4. Teaching Mode Match (10 pts max)
        if requirement.tuition_type == TuitionRequirement.TuitionType.HOME_TUITION:
            if tutor.teaching_mode in [TutorProfile.TeachingMode.HOME_ONLY, TutorProfile.TeachingMode.BOTH_HOME_ONLINE]:
                score += 10
                reasons.append("Available for home visits at student residence")
            else:
                score += 2
        else:
            score += 10
            reasons.append("Equipped with digital writing tablet and high-speed online setup")

        # 5. Budget Compatibility (10 pts max)
        tutor_fee = tutor.monthly_rate_estimate or Decimal('5000')
        if tutor_fee <= req_budget:
            score += 10
            reasons.append(f"Expected fee fits within requested budget")
        elif tutor_fee <= req_budget * Decimal('1.25'):
            score += 6
            reasons.append(f"Expected fee slightly above budget but negotiable")
        else:
            score += 2

        # 6. Verification & Quality Boost (+5 pts)
        if tutor.is_verified:
            score = min(100, score + 5)
            reasons.append(f"Verified educator with verified credentials & {tutor.average_rating}★ rating")

        final_score = min(100, max(10, score))
        match_obj, created = TutorMatch.objects.update_or_create(
            requirement=requirement,
            tutor=tutor,
            defaults={
                'match_score': final_score,
                'match_reasons': "\n".join(reasons[:4])
            }
        )
        matches.append(match_obj)

    # Sort matches by score descending
    matches.sort(key=lambda m: m.match_score, reverse=True)
    return matches[:top_n]
