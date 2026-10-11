from django.shortcuts import render, redirect
from django.contrib import messages
from apps.core.models import CompanySettings, ThemeSettings, Announcement
from apps.tutors.models import TutorProfile, TutorSubject
from apps.leads.models import TuitionRequirement
from apps.billing.models import SubscriptionPlan
from apps.engagements.models import Review, TuitionEngagement

def home_view(request):
    company = CompanySettings.get_settings()
    
    # Featured & Top rated verified tutors
    featured_tutors = TutorProfile.objects.filter(
        verification_status=TutorProfile.VerificationStatus.VERIFIED
    ).select_related('user').prefetch_related('subjects')[:6]

    # Live open tuition requirements (leads)
    recent_leads = TuitionRequirement.objects.filter(
        status=TuitionRequirement.Status.OPEN
    ).order_by('-created_at')[:6]

    # Published announcements
    announcements = Announcement.objects.filter(is_published=True)[:3]

    # Verified reviews
    reviews = Review.objects.filter(is_approved=True).select_related('tutor__user', 'parent__user')[:4]

    # Platform Stats from actual database counts
    total_tutors = TutorProfile.objects.filter(verification_status=TutorProfile.VerificationStatus.VERIFIED).count()
    total_leads = TuitionRequirement.objects.count()
    total_engagements = TuitionEngagement.objects.count()

    context = {
        'featured_tutors': featured_tutors,
        'recent_leads': recent_leads,
        'announcements': announcements,
        'reviews': reviews,
        'total_tutors': total_tutors,
        'total_leads': total_leads,
        'total_engagements': total_engagements,
    }
    return render(request, 'core/home.html', context)

def how_it_works_view(request):
    return render(request, 'core/how_it_works.html')

def pricing_view(request):
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('sort_order', 'price')
    return render(request, 'core/pricing.html', {'plans': plans})

def about_view(request):
    return render(request, 'core/about.html')

def contact_view(request):
    if request.method == 'POST':
        messages.success(request, "Thank you! Your message has been received by our support team.")
        return redirect('core:contact')
    return render(request, 'core/contact.html')

def terms_view(request):
    return render(request, 'core/terms.html')

def privacy_view(request):
    return render(request, 'core/privacy.html')
