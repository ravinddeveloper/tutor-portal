from rest_framework import serializers
from apps.tutors.models import TutorProfile, TutorSubject, TutorAvailability
from apps.leads.models import TuitionRequirement, LeadApplication, TutorMatch
from apps.billing.models import SubscriptionPlan
from apps.core.models import CompanySettings
from apps.engagements.models import DemoClass

class TutorSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorSubject
        fields = ['id', 'subject_name', 'classes_offered', 'curriculum', 'fee_per_month']

class TutorAvailabilitySerializer(serializers.ModelSerializer):
    slot_label = serializers.CharField(source='get_slot_display', read_only=True)
    day_label = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = TutorAvailability
        fields = ['id', 'day_of_week', 'day_label', 'slot', 'slot_label', 'is_active']

class TutorProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='display_name', read_only=True)
    subjects = TutorSubjectSerializer(many=True, read_only=True)
    availabilities = TutorAvailabilitySerializer(many=True, read_only=True)

    class Meta:
        model = TutorProfile
        fields = [
            'id', 'full_name', 'headline', 'bio', 'highest_qualification',
            'experience_years', 'primary_city', 'primary_locality',
            'service_radius_km', 'teaching_mode', 'monthly_rate_estimate',
            'hourly_rate', 'languages_spoken', 'verification_status',
            'is_featured', 'average_rating', 'total_reviews',
            'subjects', 'availabilities'
        ]

class PublicTuitionLeadSerializer(serializers.ModelSerializer):
    """
    Public lead serializer: hides sensitive contact details (phone, full address, email)
    to protect parent privacy until authorized unlock.
    """
    posted_ago = serializers.CharField(source='created_at', read_only=True)

    class Meta:
        model = TuitionRequirement
        fields = [
            'id', 'lead_id', 'title', 'student_class', 'board_curriculum',
            'subjects', 'tuition_type', 'city', 'locality', 'preferred_gender',
            'days_per_week', 'preferred_timing', 'budget_amount', 'budget_type',
            'credits_to_unlock', 'status', 'created_at', 'posted_ago'
        ]

class UnlockedTuitionLeadSerializer(serializers.ModelSerializer):
    """
    Unlocked lead serializer: exposes contact name, phone, email, and address
    strictly for tutors who have unlocked this lead.
    """
    class Meta:
        model = TuitionRequirement
        fields = [
            'id', 'lead_id', 'title', 'student_class', 'board_curriculum',
            'subjects', 'tuition_type', 'city', 'locality', 'preferred_gender',
            'days_per_week', 'preferred_timing', 'budget_amount', 'budget_type',
            'parent_contact_name', 'contact_phone', 'contact_email', 'full_address',
            'special_instructions', 'credits_to_unlock', 'status', 'created_at'
        ]

class TutorMatchSerializer(serializers.ModelSerializer):
    tutor_name = serializers.CharField(source='tutor.display_name', read_only=True)
    tutor_city = serializers.CharField(source='tutor.primary_city', read_only=True)
    tutor_locality = serializers.CharField(source='tutor.primary_locality', read_only=True)
    reasons_list = serializers.ListField(source='reasons_list', read_only=True)

    class Meta:
        model = TutorMatch
        fields = [
            'id', 'tutor_id', 'tutor_name', 'tutor_city', 'tutor_locality',
            'match_score', 'reasons_list', 'is_recommended_by_admin', 'created_at'
        ]

class LeadApplicationSerializer(serializers.ModelSerializer):
    tutor_name = serializers.CharField(source='tutor.display_name', read_only=True)

    class Meta:
        model = LeadApplication
        fields = [
            'id', 'requirement_id', 'tutor_id', 'tutor_name',
            'proposed_monthly_fee', 'cover_message', 'status', 'created_at'
        ]

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'slug', 'tagline', 'price', 'duration_days',
            'lead_credits_included', 'free_contact_unlocks', 'is_featured_badge',
            'priority_matching', 'commission_discount_percentage', 'is_active'
        ]

class CompanySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySettings
        fields = [
            'company_name', 'tagline', 'support_email', 'support_phone',
            'whatsapp_number', 'currency_symbol', 'currency_code',
            'tax_percentage', 'tax_name', 'commission_enabled'
        ]
