from rest_framework import views, generics, status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q

from apps.tutors.models import TutorProfile
from apps.leads.models import TuitionRequirement, TutorMatch, LeadUnlock
from apps.leads.services import unlock_lead_for_tutor
from apps.leads.matching import run_tutor_matching
from apps.billing.models import SubscriptionPlan
from apps.core.models import CompanySettings

from .serializers import (
    TutorProfileSerializer, PublicTuitionLeadSerializer,
    UnlockedTuitionLeadSerializer, TutorMatchSerializer,
    SubscriptionPlanSerializer, CompanySettingsSerializer
)

class TutorListAPIView(generics.ListAPIView):
    """
    Public directory of verified tutors with search and filtering by
    subject, city, class, teaching mode.
    """
    serializer_class = TutorProfileSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = TutorProfile.objects.filter(
            verification_status=TutorProfile.VerificationStatus.VERIFIED
        ).prefetch_related('subjects', 'availabilities')

        city = self.request.query_params.get('city')
        subject = self.request.query_params.get('subject')
        mode = self.request.query_params.get('mode')
        q = self.request.query_params.get('q')

        if city:
            qs = qs.filter(primary_city__icontains=city)
        if subject:
            qs = qs.filter(subjects__subject_name__icontains=subject)
        if mode:
            qs = qs.filter(teaching_mode=mode)
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(headline__icontains=q) |
                Q(subjects__subject_name__icontains=q)
            ).distinct()

        return qs

class TutorDetailAPIView(generics.RetrieveAPIView):
    """Detail of a single verified tutor profile."""
    queryset = TutorProfile.objects.all().prefetch_related('subjects', 'availabilities')
    serializer_class = TutorProfileSerializer
    permission_classes = [permissions.AllowAny]

class PublicLeadsListAPIView(generics.ListAPIView):
    """
    Public feed of open tuition requirements.
    Masks parent phone number and home address to protect privacy.
    """
    serializer_class = PublicTuitionLeadSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = TuitionRequirement.objects.filter(
            status__in=[TuitionRequirement.Status.OPEN, TuitionRequirement.Status.MATCHING]
        ).order_by('-created_at')

        city = self.request.query_params.get('city')
        subject = self.request.query_params.get('subject')
        tuition_type = self.request.query_params.get('type')

        if city:
            qs = qs.filter(city__icontains=city)
        if subject:
            qs = qs.filter(subjects__icontains=subject)
        if tuition_type:
            qs = qs.filter(tuition_type=tuition_type)

        return qs

class LeadDetailAPIView(views.APIView):
    """
    Retrieves lead details. If authenticated tutor has unlocked this lead,
    returns full unmasked contact details. Otherwise returns masked view.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, lead_id):
        lead = get_object_or_404(TuitionRequirement, lead_id=lead_id)
        is_unlocked = False

        if request.user.is_authenticated and hasattr(request.user, 'tutor_profile'):
            tutor = request.user.tutor_profile
            is_unlocked = lead.is_unlocked_by(tutor)

        if is_unlocked:
            serializer = UnlockedTuitionLeadSerializer(lead)
        else:
            serializer = PublicTuitionLeadSerializer(lead)

        data = serializer.data
        data['is_unlocked_by_viewer'] = is_unlocked
        return Response(data)

class UnlockLeadAPIView(views.APIView):
    """
    Atomically unlocks a tuition lead for the authenticated tutor
    using their contact credit balance.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, lead_id):
        if not hasattr(request.user, 'tutor_profile'):
            return Response(
                {"detail": "Only registered tutors can unlock tuition leads."},
                status=status.HTTP_403_FORBIDDEN
            )

        tutor = request.user.tutor_profile
        lead = get_object_or_404(TuitionRequirement, lead_id=lead_id)

        success, msg, data = unlock_lead_for_tutor(lead, tutor)
        if not success:
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": True,
            "message": msg,
            "contact_details": data
        }, status=status.HTTP_200_OK)

class LeadMatchesAPIView(views.APIView):
    """
    Triggers or retrieves tutor matches for a specific tuition requirement.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, lead_id):
        lead = get_object_or_404(TuitionRequirement, lead_id=lead_id)
        # Check permissions: only requirement owner or staff can view
        if not (request.user.is_staff or (hasattr(request.user, 'parent_profile') and lead.parent == request.user.parent_profile)):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        matches = run_tutor_matching(lead)
        serializer = TutorMatchSerializer(matches, many=True)
        return Response({
            "lead_id": lead.lead_id,
            "total_matches": len(matches),
            "matches": serializer.data
        })

class SubscriptionPlansAPIView(generics.ListAPIView):
    """Lists available subscription plans."""
    queryset = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]

class CompanyConfigAPIView(views.APIView):
    """Public platform branding and configuration."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        company = CompanySettings.get_settings()
        serializer = CompanySettingsSerializer(company)
        return Response(serializer.data)
