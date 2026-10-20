from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone

from apps.tutors.models import (
    TutorProfile, TutorSubject, TutorQualification, TutorDocument, TutorAvailability, SavedTutor, TutorPipelineCard
)
from apps.leads.models import TuitionRequirement, TutorMatch, LeadUnlock, LeadApplication
from apps.leads.services import unlock_lead_for_tutor
from apps.engagements.models import DemoClass, TuitionEngagement, LessonSchedule, LessonRecord, StudentProgressReport
from apps.billing.models import ContactCreditWallet, TutorSubscription, SubscriptionPlan, CommissionRecord, Invoice
from apps.communication.models import Notification

def directory_view(request):
    """Public searchable tutor directory with rich multi-faceted filters and explainable matching."""
    qs = TutorProfile.objects.filter(
        verification_status=TutorProfile.VerificationStatus.VERIFIED
    ).select_related('user').prefetch_related('subjects', 'qualifications')

    # Filters
    subject_q = request.GET.get('subject', '').strip()
    if subject_q:
        qs = qs.filter(
            Q(subjects__subject_name__icontains=subject_q) |
            Q(headline__icontains=subject_q) |
            Q(bio__icontains=subject_q)
        ).distinct()

    city_q = request.GET.get('city', '').strip()
    if city_q:
        qs = qs.filter(
            Q(primary_city__icontains=city_q) |
            Q(primary_locality__icontains=city_q)
        )

    class_q = request.GET.get('student_class', '').strip()
    if class_q:
        qs = qs.filter(
            Q(subjects__classes_offered__icontains=class_q) |
            Q(headline__icontains=class_q) |
            Q(bio__icontains=class_q)
        ).distinct()

    mode_q = request.GET.get('teaching_mode', '').strip()
    if mode_q:
        qs = qs.filter(teaching_mode=mode_q)

    gender_q = request.GET.get('gender', '').strip()
    if gender_q:
        qs = qs.filter(gender=gender_q)

    # Sorting
    sort_by = request.GET.get('sort', 'rating')
    if sort_by == 'rating':
        qs = qs.order_by('-average_rating', '-total_reviews')
    elif sort_by == 'experience':
        qs = qs.order_by('-experience_years')
    elif sort_by == 'fee_asc':
        qs = qs.order_by('monthly_rate_estimate')
    elif sort_by == 'fee_desc':
        qs = qs.order_by('-monthly_rate_estimate')
    else:
        qs = qs.order_by('-is_featured', '-average_rating')

    paginator = Paginator(qs, 9)
    page_number = request.GET.get('page')
    tutors_page = paginator.get_page(page_number)

    # Fetch saved tutors for the current authenticated user
    saved_tutor_ids = set()
    if request.user.is_authenticated:
        saved_tutor_ids = set(SavedTutor.objects.filter(user=request.user).values_list('tutor_id', flat=True))

    # Compute explainable match reasons for tutors on the current page
    for t in tutors_page:
        reasons = []
        if subject_q and any(subject_q.lower() in s.subject_name.lower() for s in t.subjects.all()):
            reasons.append(f"Teaches {subject_q}")
        if city_q and (city_q.lower() in t.primary_city.lower() or city_q.lower() in t.primary_locality.lower()):
            reasons.append(f"Available in {t.primary_locality or t.primary_city}")
        if mode_q and t.teaching_mode == mode_q:
            reasons.append(f"Offers {t.get_teaching_mode_display()}")
        if t.is_verified:
            reasons.append("Background Verified")
        if t.experience_years >= 5:
            reasons.append(f"{t.experience_years}+ Yrs Experience")
        if t.average_rating >= 4.8:
            reasons.append(f"Top Rated ({t.average_rating}★)")
        t.match_reasons_list = reasons[:3]

    context = {
        'tutors': tutors_page,
        'subject_q': subject_q,
        'city_q': city_q,
        'class_q': class_q,
        'mode_q': mode_q,
        'gender_q': gender_q,
        'sort_by': sort_by,
        'total_results': paginator.count,
        'saved_tutor_ids': saved_tutor_ids,
        'search_query_string': request.GET.urlencode(),
    }
    return render(request, 'tutors/directory.html', context)

def detail_view(request, pk):
    """Public tutor profile page with qualifications, reviews, and demo booking form."""
    tutor = get_object_or_404(
        TutorProfile.objects.select_related('user').prefetch_related('subjects', 'qualifications', 'reviews__parent__user', 'availabilities'),
        pk=pk
    )

    is_saved = False
    if request.user.is_authenticated:
        is_saved = SavedTutor.objects.filter(user=request.user, tutor=tutor).exists()

    # Demo request form handling
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.info(request, "Please log in as a parent or student to schedule a trial demo class.")
            return redirect(f"/accounts/login/?next=/tutors/{pk}/")

        if not request.user.is_parent:
            messages.warning(request, "Only registered parents and students can book demo classes.")
            return redirect('tutors:detail', pk=pk)

        sched_date = request.POST.get('scheduled_datetime')
        demo_mode = request.POST.get('mode', DemoClass.Mode.ONLINE)
        req_id = request.POST.get('requirement_id')
        notes = request.POST.get('notes', '')

        # Find or pick an active requirement for this parent
        req_obj = None
        if req_id:
            req_obj = TuitionRequirement.objects.filter(pk=req_id, parent=request.user.parent_profile).first()
        if not req_obj:
            req_obj = TuitionRequirement.objects.filter(parent=request.user.parent_profile).first()

        if not req_obj:
            messages.warning(request, "Please post your tuition requirement first before scheduling a demo class.")
            return redirect('leads:post_requirement')

        if sched_date:
            demo = DemoClass.objects.create(
                requirement=req_obj,
                tutor=tutor,
                parent=request.user.parent_profile,
                mode=demo_mode,
                scheduled_datetime=sched_date,
                status=DemoClass.Status.REQUESTED,
                tutor_notes=notes
            )
            Notification.objects.create(
                user=tutor.user,
                title="New Demo Class Request",
                message=f"Parent {request.user.display_name} requested a {demo_mode} demo class on {sched_date}.",
                notification_type=Notification.Type.DEMO_ALERT,
                action_url="/tutors/demos/"
            )
            messages.success(request, f"Demo class requested successfully with {tutor.display_name}! The tutor has been notified.")
            return redirect('parents:demos')

    user_requirements = []
    if request.user.is_authenticated and request.user.is_parent:
        user_requirements = TuitionRequirement.objects.filter(parent=request.user.parent_profile, status=TuitionRequirement.Status.OPEN)

    context = {
        'tutor': tutor,
        'user_requirements': user_requirements,
        'is_saved': is_saved,
    }
    return render(request, 'tutors/detail.html', context)

@login_required
def toggle_save_tutor_view(request, pk):
    """AJAX or standard POST endpoint to toggle saved/shortlist status of a tutor."""
    tutor = get_object_or_404(TutorProfile, pk=pk)
    saved_obj = SavedTutor.objects.filter(user=request.user, tutor=tutor).first()

    if saved_obj:
        saved_obj.delete()
        is_saved = False
        msg = f"{tutor.display_name} removed from your saved tutors."
    else:
        SavedTutor.objects.create(user=request.user, tutor=tutor)
        is_saved = True
        msg = f"{tutor.display_name} saved to your shortlist!"

    total_saved = SavedTutor.objects.filter(user=request.user).count()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({
            'success': True,
            'saved': is_saved,
            'message': msg,
            'total_saved': total_saved
        })

    messages.success(request, msg)
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('tutors:directory')

@login_required
def saved_tutors_view(request):
    """View all shortlisted / bookmarked tutors for the authenticated user."""
    saved_entries = SavedTutor.objects.filter(user=request.user).select_related(
        'tutor__user'
    ).prefetch_related('tutor__subjects', 'tutor__qualifications')

    context = {
        'saved_entries': saved_entries,
        'total_saved': saved_entries.count(),
    }
    return render(request, 'tutors/saved_tutors.html', context)

def tutor_compare_view(request):
    """Side-by-side comparative analysis of selected tutors."""
    raw_ids = request.GET.get('ids', '').split(',')
    tutor_ids = [int(i.strip()) for i in raw_ids if i.strip().isdigit()][:4]

    tutors = []
    if tutor_ids:
        tutors = list(TutorProfile.objects.filter(
            pk__in=tutor_ids,
            verification_status=TutorProfile.VerificationStatus.VERIFIED
        ).select_related('user').prefetch_related('subjects', 'qualifications', 'availabilities'))

    saved_tutor_ids = set()
    if request.user.is_authenticated:
        saved_tutor_ids = set(SavedTutor.objects.filter(user=request.user).values_list('tutor_id', flat=True))

    context = {
        'tutors': tutors,
        'saved_tutor_ids': saved_tutor_ids,
        'tutor_ids_str': ','.join(str(t.id) for t in tutors),
    }
    return render(request, 'tutors/compare.html', context)


@login_required
def dashboard_view(request):
    """
    Tutor portal private dashboard with wallet stats, Smart Lead Radar,
    Kanban-style Demo Class Pipeline, and gamified Profile Strength meter.
    """
    if not request.user.is_tutor:
        messages.error(request, "Unauthorized access. Tutor account required.")
        return redirect('accounts:dashboard_redirect')

    tprofile = get_object_or_404(TutorProfile, user=request.user)
    wallet = ContactCreditWallet.get_or_create_wallet(tprofile)
    active_subscription = TutorSubscription.objects.filter(
        tutor=tprofile, status=TutorSubscription.Status.ACTIVE, end_date__gte=timezone.now().date()
    ).first()

    # Lead recommendations via TutorMatch
    matched_leads = list(TutorMatch.objects.filter(
        tutor=tprofile, requirement__status=TuitionRequirement.Status.OPEN
    ).select_related('requirement').order_by('-match_score')[:6])

    if not matched_leads:
        from apps.leads.matching import run_tutor_matching
        open_reqs = TuitionRequirement.objects.filter(status=TuitionRequirement.Status.OPEN)[:4]
        for req in open_reqs:
            run_tutor_matching(req, top_n=2)
        matched_leads = list(TutorMatch.objects.filter(
            tutor=tprofile, requirement__status=TuitionRequirement.Status.OPEN
        ).select_related('requirement').order_by('-match_score')[:6])

    # 1. SMART LEAD RADAR (Match Alert)
    radar_lead = matched_leads[0] if matched_leads else None
    radar_alert = None
    if radar_lead:
        radar_alert = {
            'active': True,
            'lead_id': radar_lead.requirement.lead_id,
            'title': radar_lead.requirement.title,
            'subjects': radar_lead.requirement.subjects,
            'student_class': radar_lead.requirement.student_class,
            'board_curriculum': radar_lead.requirement.board_curriculum,
            'locality': radar_lead.requirement.locality,
            'city': radar_lead.requirement.city,
            'budget_amount': radar_lead.requirement.budget_amount,
            'match_score': radar_lead.match_score,
            'match_reasons': radar_lead.match_reasons,
            'toast_message': f"Urgent: A {radar_lead.requirement.student_class} {radar_lead.requirement.subjects} lead in your area ({radar_lead.requirement.locality}) just went live!",
        }

    # 2. DEMO CLASS KANBAN PIPELINE (Auto-sync & Card Aggregation)
    for unlock in LeadUnlock.objects.filter(tutor=tprofile).select_related('requirement'):
        TutorPipelineCard.objects.get_or_create(
            tutor=tprofile,
            requirement=unlock.requirement,
            defaults={
                'stage': TutorPipelineCard.Stage.APPLIED,
                'estimated_monthly_value': unlock.requirement.budget_amount or Decimal('5000')
            }
        )

    for demo in DemoClass.objects.filter(tutor=tprofile).select_related('requirement'):
        initial_stage = TutorPipelineCard.Stage.DEMO_SCHEDULED if demo.status != DemoClass.Status.COMPLETED else TutorPipelineCard.Stage.DEMO_COMPLETED
        TutorPipelineCard.objects.get_or_create(
            tutor=tprofile,
            requirement=demo.requirement,
            defaults={
                'stage': initial_stage,
                'estimated_monthly_value': demo.requirement.budget_amount or Decimal('5000')
            }
        )

    for eng in TuitionEngagement.objects.filter(tutor=tprofile).select_related('requirement'):
        TutorPipelineCard.objects.get_or_create(
            tutor=tprofile,
            requirement=eng.requirement,
            defaults={
                'stage': TutorPipelineCard.Stage.WON,
                'estimated_monthly_value': eng.agreed_fee or Decimal('6000')
            }
        )

    # Seed sample cards if none exist to enable immediate drag-and-drop exploration
    existing_cards_count = TutorPipelineCard.objects.filter(tutor=tprofile).count()
    if existing_cards_count == 0:
        sample_reqs = list(TuitionRequirement.objects.all()[:4])
        stages = [
            TutorPipelineCard.Stage.APPLIED,
            TutorPipelineCard.Stage.DEMO_SCHEDULED,
            TutorPipelineCard.Stage.DEMO_COMPLETED,
            TutorPipelineCard.Stage.WON
        ]
        for i, s_req in enumerate(sample_reqs):
            TutorPipelineCard.objects.create(
                tutor=tprofile,
                requirement=s_req,
                stage=stages[i % len(stages)],
                estimated_monthly_value=s_req.budget_amount or Decimal('5500')
            )

    all_pipeline_cards = list(TutorPipelineCard.objects.filter(tutor=tprofile).select_related('requirement__parent__user'))
    pipeline_applied = [c for c in all_pipeline_cards if c.stage == TutorPipelineCard.Stage.APPLIED]
    pipeline_demo_scheduled = [c for c in all_pipeline_cards if c.stage == TutorPipelineCard.Stage.DEMO_SCHEDULED]
    pipeline_demo_completed = [c for c in all_pipeline_cards if c.stage == TutorPipelineCard.Stage.DEMO_COMPLETED]
    pipeline_won = [c for c in all_pipeline_cards if c.stage == TutorPipelineCard.Stage.WON]
    pipeline_lost = [c for c in all_pipeline_cards if c.stage == TutorPipelineCard.Stage.LOST]
    total_pipeline_value = sum(c.estimated_monthly_value for c in all_pipeline_cards)

    # Upcoming Demos
    upcoming_demos = DemoClass.objects.filter(
        tutor=tprofile, status__in=[DemoClass.Status.REQUESTED, DemoClass.Status.PROPOSED, DemoClass.Status.CONFIRMED]
    ).select_related('parent__user', 'requirement')[:5]

    # Active Tuition Engagements
    active_engagements = TuitionEngagement.objects.filter(
        tutor=tprofile, status=TuitionEngagement.Status.ACTIVE
    ).select_related('parent__user')

    # Commission status
    pending_commissions = CommissionRecord.objects.filter(
        tutor=tprofile, status=CommissionRecord.Status.PENDING
    )

    completeness = tprofile.calculate_completeness()

    context = {
        'tutor': tprofile,
        'wallet': wallet,
        'active_subscription': active_subscription,
        'matched_leads': matched_leads,
        'upcoming_demos': upcoming_demos,
        'active_engagements': active_engagements,
        'pending_commissions': pending_commissions,
        'completeness': completeness,

        # Gamification Badges
        'ranking_badge': tprofile.ranking_badge,
        'is_fast_responder': tprofile.is_fast_responder,
        'is_top_ranked': tprofile.is_top_ranked,

        # Smart Lead Radar Alert
        'radar_alert': radar_alert,

        # Kanban Board Pipeline
        'pipeline_applied': pipeline_applied,
        'pipeline_demo_scheduled': pipeline_demo_scheduled,
        'pipeline_demo_completed': pipeline_demo_completed,
        'pipeline_won': pipeline_won,
        'pipeline_lost': pipeline_lost,
        'total_pipeline_value': total_pipeline_value,
        'total_pipeline_count': len(all_pipeline_cards),
    }
    return render(request, 'tutors/dashboard.html', context)

@login_required
def pipeline_update_view(request):
    """
    AJAX endpoint for Drag & Drop Kanban stage updates.
    Accepts card_id and new_stage, persists change, and returns JSON status.
    """
    if not request.user.is_tutor:
        return JsonResponse({'success': False, 'error': 'Unauthorized access'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)

    tprofile = get_object_or_404(TutorProfile, user=request.user)
    
    card_id = request.POST.get('card_id')
    new_stage = request.POST.get('stage')

    if not card_id or not new_stage:
        return JsonResponse({'success': False, 'error': 'Missing card_id or stage'}, status=400)

    if new_stage not in TutorPipelineCard.Stage.values:
        return JsonResponse({'success': False, 'error': f'Invalid stage: {new_stage}'}, status=400)

    card = get_object_or_404(TutorPipelineCard, pk=card_id, tutor=tprofile)
    card.stage = new_stage
    card.save(update_fields=['stage', 'updated_at'])

    return JsonResponse({
        'success': True,
        'message': f"Lead {card.requirement.lead_id} successfully moved to '{card.get_stage_display()}'.",
        'card_id': card.id,
        'new_stage': card.stage,
        'stage_display': card.get_stage_display()
    })

@login_required
def profile_edit_view(request):
    if not request.user.is_tutor:
        return redirect('accounts:dashboard_redirect')

    tprofile = get_object_or_404(TutorProfile, user=request.user)

    if request.method == 'POST':
        tprofile.headline = request.POST.get('headline', '').strip()
        tprofile.bio = request.POST.get('bio', '').strip()
        tprofile.demo_video_url = request.POST.get('demo_video_url', '').strip()
        tprofile.gender = request.POST.get('gender', TutorProfile.Gender.MALE)
        tprofile.experience_years = int(request.POST.get('experience_years', 2) or 2)
        tprofile.highest_qualification = request.POST.get('highest_qualification', '').strip()
        tprofile.institution_name = request.POST.get('institution_name', '').strip()
        tprofile.teaching_mode = request.POST.get('teaching_mode', TutorProfile.TeachingMode.BOTH_HOME_ONLINE)
        tprofile.hourly_rate = Decimal(request.POST.get('hourly_rate', 500) or 500)
        tprofile.monthly_rate_estimate = Decimal(request.POST.get('monthly_rate_estimate', 5000) or 5000)
        tprofile.primary_city = request.POST.get('primary_city', 'Bengaluru').strip()
        tprofile.primary_locality = request.POST.get('primary_locality', '').strip()
        tprofile.service_radius_km = int(request.POST.get('service_radius_km', 10) or 10)
        tprofile.languages_spoken = request.POST.get('languages_spoken', 'English, Hindi').strip()
        tprofile.online_tools = request.POST.get('online_tools', '').strip()
        tprofile.save()

        # Update user first and last name
        request.user.first_name = request.POST.get('first_name', request.user.first_name).strip()
        request.user.last_name = request.POST.get('last_name', request.user.last_name).strip()
        request.user.phone_number = request.POST.get('phone_number', request.user.phone_number).strip()
        request.user.save()

        messages.success(request, "Tutor profile updated successfully.")
        return redirect('tutors:profile_edit')

    return render(request, 'tutors/profile_edit.html', {'tutor': tprofile})

    return render(request, 'tutors/profile_edit.html', {'tutor': tprofile})

@login_required
def subjects_manage_view(request):
    if not request.user.is_tutor:
        return redirect('accounts:dashboard_redirect')

    tprofile = get_object_or_404(TutorProfile, user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            subject_name = request.POST.get('subject_name', '').strip()
            classes_offered = request.POST.get('classes_offered', '').strip()
            curriculum = request.POST.get('curriculum', 'CBSE, ICSE').strip()
            fee = Decimal(request.POST.get('fee_per_month', 5000) or 5000)
            if subject_name:
                TutorSubject.objects.update_or_create(
                    tutor=tprofile,
                    subject_name=subject_name,
                    defaults={
                        'classes_offered': classes_offered,
                        'curriculum': curriculum,
                        'fee_per_month': fee
                    }
                )
                messages.success(request, f"Subject '{subject_name}' added successfully.")
        elif action == 'delete':
            sub_id = request.POST.get('subject_id')
            TutorSubject.objects.filter(pk=sub_id, tutor=tprofile).delete()
            messages.info(request, "Subject removed.")
        return redirect('tutors:subjects_manage')

    subjects = TutorSubject.objects.filter(tutor=tprofile)
    return render(request, 'tutors/subjects_manage.html', {'tutor': tprofile, 'subjects': subjects})

@login_required
def availability_manage_view(request):
    if not request.user.is_tutor:
        return redirect('accounts:dashboard_redirect')

    tprofile = get_object_or_404(TutorProfile, user=request.user)

    if request.method == 'POST':
        # Clear existing active slots and set new ones
        TutorAvailability.objects.filter(tutor=tprofile).delete()
        selected_slots = request.POST.getlist('slots') # e.g. "0-EVENING", "1-MORNING"
        for s in selected_slots:
            parts = s.split('-')
            if len(parts) == 2:
                day_idx = int(parts[0])
                slot_name = parts[1]
                TutorAvailability.objects.create(
                    tutor=tprofile,
                    day_of_week=day_idx,
                    slot=slot_name,
                    is_active=True
                )
        messages.success(request, "Weekly schedule availability updated successfully.")
        return redirect('tutors:availability_manage')

    existing_slots = set(
        f"{a.day_of_week}-{a.slot}" for a in TutorAvailability.objects.filter(tutor=tprofile, is_active=True)
    )
    days = TutorAvailability.DayOfWeek.choices
    slots = TutorAvailability.Slot.choices

    return render(request, 'tutors/availability_manage.html', {
        'tutor': tprofile,
        'existing_slots': existing_slots,
        'days': days,
        'slots': slots,
    })

@login_required
def documents_upload_view(request):
    if not request.user.is_tutor:
        return redirect('accounts:dashboard_redirect')

    tprofile = get_object_or_404(TutorProfile, user=request.user)

    if request.method == 'POST':
        doc_type = request.POST.get('document_type', TutorDocument.DocumentType.GOVT_ID)
        doc_name = request.POST.get('document_name', '').strip()
        doc_url = request.POST.get('document_url', '').strip()
        doc_file = request.FILES.get('document_file')

        TutorDocument.objects.create(
            tutor=tprofile,
            document_type=doc_type,
            document_name=doc_name or f"Verification Document ({doc_type})",
            document_file=doc_file,
            document_url=doc_url or "https://storage.googleapis.com/edututor/docs/verified_sample.pdf",
            status=TutorDocument.Status.PENDING
        )
        tprofile.verification_status = TutorProfile.VerificationStatus.UNDER_REVIEW
        tprofile.save(update_fields=['verification_status'])
        messages.success(request, "Document uploaded for review. Platform operations staff will verify it shortly.")
        return redirect('tutors:documents_upload')

    documents = TutorDocument.objects.filter(tutor=tprofile)
    return render(request, 'tutors/documents_upload.html', {'tutor': tprofile, 'documents': documents})

@login_required
def leads_browse_view(request):
    """Tutors browse available leads, filter, view match scores, unlock or apply."""
    if not request.user.is_tutor:
        return redirect('accounts:dashboard_redirect')

    tprofile = get_object_or_404(TutorProfile, user=request.user)
    wallet = ContactCreditWallet.get_or_create_wallet(tprofile)

    qs = TuitionRequirement.objects.filter(status=TuitionRequirement.Status.OPEN)

    # Filter by subjects or locality
    sub_q = request.GET.get('subject', '').strip()
    if sub_q:
        qs = qs.filter(subjects__icontains=sub_q)
    city_q = request.GET.get('city', '').strip()
    if city_q:
        qs = qs.filter(Q(city__icontains=city_q) | Q(locality__icontains=city_q))

    # Lead unlocking post action
    if request.method == 'POST' and request.POST.get('action') == 'unlock':
        lead_id = request.POST.get('lead_id')
        req_obj = get_object_or_404(TuitionRequirement, lead_id=lead_id)
        success, msg, data = unlock_lead_for_tutor(req_obj, tprofile)
        if success:
            messages.success(request, msg)
            return redirect('tutors:unlocked_leads')
        else:
            messages.error(request, msg)

    # Lead proposal application
    if request.method == 'POST' and request.POST.get('action') == 'apply':
        lead_id = request.POST.get('lead_id')
        req_obj = get_object_or_404(TuitionRequirement, lead_id=lead_id)
        note = request.POST.get('cover_note', '').strip()
        fee = Decimal(request.POST.get('proposed_fee', req_obj.budget_amount) or req_obj.budget_amount)
        
        LeadApplication.objects.update_or_create(
            requirement=req_obj,
            tutor=tprofile,
            defaults={'cover_note': note, 'proposed_fee': fee, 'status': LeadApplication.Status.PENDING}
        )
        req_obj.total_applications += 1
        req_obj.save(update_fields=['total_applications'])
        messages.success(request, f"Application proposal submitted to parent for lead {req_obj.lead_id}!")
        return redirect('tutors:applications')

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    leads_page = paginator.get_page(page_number)

    unlocked_lead_ids = set(
        LeadUnlock.objects.filter(tutor=tprofile).values_list('requirement__lead_id', flat=True)
    )

    context = {
        'tutor': tprofile,
        'wallet': wallet,
        'leads': leads_page,
        'unlocked_lead_ids': unlocked_lead_ids,
        'sub_q': sub_q,
        'city_q': city_q,
    }
    return render(request, 'tutors/leads_browse.html', context)

@login_required
def unlocked_leads_view(request):
    """List of parent contact details unlocked by this tutor, with outcome feedback."""
    if not request.user.is_tutor:
        return redirect('accounts:dashboard_redirect')

    tprofile = get_object_or_404(TutorProfile, user=request.user)

    # Handle feedback submission or credit replacement request
    if request.method == 'POST':
        unlock_id = request.POST.get('unlock_id')
        feedback = request.POST.get('feedback_status')
        note = request.POST.get('feedback_note', '')
        unlock_obj = get_object_or_404(LeadUnlock, pk=unlock_id, tutor=tprofile)
        unlock_obj.feedback_status = feedback
        unlock_obj.feedback_note = note
        unlock_obj.save()
        messages.success(request, "Lead feedback recorded. If a replacement credit was requested, staff will review it.")
        return redirect('tutors:unlocked_leads')

    unlocks = LeadUnlock.objects.filter(tutor=tprofile).select_related('requirement')
    return render(request, 'tutors/unlocked_leads.html', {'tutor': tprofile, 'unlocks': unlocks})

@login_required
def applications_view(request):
    if not request.user.is_tutor:
        return redirect('accounts:dashboard_redirect')

    tprofile = get_object_or_404(TutorProfile, user=request.user)
    apps = LeadApplication.objects.filter(tutor=tprofile).select_related('requirement')
    return render(request, 'tutors/applications.html', {'tutor': tprofile, 'applications': apps})

@login_required
def demos_view(request):
    if not request.user.is_tutor:
        return redirect('accounts:dashboard_redirect')

    tprofile = get_object_or_404(TutorProfile, user=request.user)

    if request.method == 'POST':
        demo_id = request.POST.get('demo_id')
        new_status = request.POST.get('status')
        notes = request.POST.get('tutor_notes', '')
        link = request.POST.get('meeting_link', '')

        demo = get_object_or_404(DemoClass, pk=demo_id, tutor=tprofile)
        if new_status:
            demo.status = new_status
        if notes:
            demo.tutor_notes = notes
        if link:
            demo.meeting_link = link
        demo.save()
        messages.success(request, f"Demo class status updated to '{demo.get_status_display()}'.")
        return redirect('tutors:demos')

    demos = DemoClass.objects.filter(tutor=tprofile).select_related('parent__user', 'requirement')
    return render(request, 'tutors/demos.html', {'tutor': tprofile, 'demos': demos})

@login_required
def engagements_view(request):
    """Manage confirmed active tuitions, lessons, attendance, and progress reports."""
    if not request.user.is_tutor:
        return redirect('accounts:dashboard_redirect')

    tprofile = get_object_or_404(TutorProfile, user=request.user)

    # Form handling for logging a lesson
    if request.method == 'POST' and request.POST.get('action') == 'add_lesson':
        eng_id = request.POST.get('engagement_id')
        eng = get_object_or_404(TuitionEngagement, pk=eng_id, tutor=tprofile)
        title = request.POST.get('title', 'Regular Tuition Class')
        date_str = request.POST.get('scheduled_datetime')
        topics = request.POST.get('topics_covered', '')
        homework = request.POST.get('homework_assigned', '')
        remarks = request.POST.get('tutor_remarks', '')

        if date_str:
            lesson = LessonSchedule.objects.create(
                engagement=eng,
                title=title,
                scheduled_datetime=date_str,
                status=LessonSchedule.Status.COMPLETED
            )
            LessonRecord.objects.create(
                lesson=lesson,
                attendance=LessonRecord.Attendance.PRESENT,
                topics_covered=topics,
                homework_assigned=homework,
                tutor_remarks=remarks
            )
            eng.total_classes_conducted += 1
            eng.save(update_fields=['total_classes_conducted'])
            messages.success(request, f"Lesson record saved for {eng.engagement_id}!")
            return redirect('tutors:engagements')

    engagements = TuitionEngagement.objects.filter(tutor=tprofile).select_related('parent__user', 'student', 'requirement').prefetch_related('lessons__record')
    return render(request, 'tutors/engagements.html', {'tutor': tprofile, 'engagements': engagements})

@login_required
def billing_view(request):
    """Wallet, credit recharges, subscriptions, and commission statements."""
    if not request.user.is_tutor:
        return redirect('accounts:dashboard_redirect')

    tprofile = get_object_or_404(TutorProfile, user=request.user)
    wallet = ContactCreditWallet.get_or_create_wallet(tprofile)
    active_sub = TutorSubscription.objects.filter(
        tutor=tprofile, status=TutorSubscription.Status.ACTIVE, end_date__gte=timezone.now().date()
    ).first()
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('sort_order')
    transactions = wallet.transactions.all()[:15]
    commissions = CommissionRecord.objects.filter(tutor=tprofile).order_by('-created_at')
    invoices = Invoice.objects.filter(user=request.user).order_by('-created_at')

    # Simulate Commission Payment
    if request.method == 'POST' and request.POST.get('action') == 'pay_commission':
        comm_id = request.POST.get('commission_id')
        comm = get_object_or_404(CommissionRecord, pk=comm_id, tutor=tprofile)
        comm.status = CommissionRecord.Status.PAID
        comm.paid_at = timezone.now()
        comm.save()
        messages.success(request, f"Commission invoice {comm.record_id} marked as Paid & Settled.")
        return redirect('tutors:billing')

    context = {
        'tutor': tprofile,
        'wallet': wallet,
        'active_sub': active_sub,
        'plans': plans,
        'transactions': transactions,
        'commissions': commissions,
        'invoices': invoices,
    }
    return render(request, 'tutors/billing.html', context)
