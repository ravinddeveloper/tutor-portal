import os
from django.conf import settings
from django.http import FileResponse, Http404
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
    total_subjects = TutorSubject.objects.values('subject_name').distinct().count()

    # Popular subject categories with Lucide icon names and accent colors
    popular_subjects = [
        {'name': 'Mathematics', 'icon': 'calculator', 'color': '#4f46e5', 'bg': 'rgba(79, 70, 229, 0.1)'},
        {'name': 'Physics', 'icon': 'zap', 'color': '#0891b2', 'bg': 'rgba(8, 145, 178, 0.1)'},
        {'name': 'Chemistry', 'icon': 'flask-conical', 'color': '#059669', 'bg': 'rgba(5, 150, 105, 0.1)'},
        {'name': 'Biology', 'icon': 'dna', 'color': '#16a34a', 'bg': 'rgba(22, 163, 74, 0.1)'},
        {'name': 'English', 'icon': 'book-open', 'color': '#7c3aed', 'bg': 'rgba(124, 58, 237, 0.1)'},
        {'name': 'Computer Science', 'icon': 'monitor', 'color': '#2563eb', 'bg': 'rgba(37, 99, 235, 0.1)'},
        {'name': 'Science', 'icon': 'microscope', 'color': '#059669', 'bg': 'rgba(5, 150, 105, 0.1)'},
        {'name': 'Social Studies', 'icon': 'globe', 'color': '#d97706', 'bg': 'rgba(217, 119, 6, 0.1)'},
    ]

    # Calculate real tutor counts per subject from database
    subject_counts = {}
    for item in TutorSubject.objects.filter(
        tutor__verification_status=TutorProfile.VerificationStatus.VERIFIED
    ).values('subject_name'):
        s_name = item['subject_name'].strip().lower()
        subject_counts[s_name] = subject_counts.get(s_name, 0) + 1

    for subj in popular_subjects:
        subj['tutor_count'] = subject_counts.get(subj['name'].lower(), 0)

    context = {
        'featured_tutors': featured_tutors,
        'recent_leads': recent_leads,
        'announcements': announcements,
        'reviews': reviews,
        'total_tutors': total_tutors,
        'total_leads': total_leads,
        'total_engagements': total_engagements,
        'total_subjects': total_subjects,
        'popular_subjects': popular_subjects,
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


def serve_dmsans_font(request, *args, **kwargs):
    """
    Serve DMSans-Regular.ttf font to gracefully satisfy requests from
    browser extensions, developer tools, or relative font links without throwing a 404.
    """
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DMSans-Regular.ttf')
    if os.path.exists(font_path):
        response = FileResponse(open(font_path, 'rb'), content_type='font/ttf')
        response['Cache-Control'] = 'public, max-age=31536000'
        return response
    raise Http404("Font file not found")

