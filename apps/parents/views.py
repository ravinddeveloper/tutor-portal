import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone

from apps.parents.models import ParentProfile, StudentProfile
from apps.leads.models import TuitionRequirement, TutorMatch, LeadApplication
from apps.engagements.models import DemoClass, TuitionEngagement, Review, LessonSchedule, LessonRecord, StudentProgressReport
from apps.tutors.models import TutorProfile, TutorPipelineCard, TutorAvailability
from apps.billing.services import generate_commission_for_engagement
from apps.communication.models import Notification

@login_required
def dashboard_view(request):
    if not request.user.is_parent:
        return redirect('accounts:dashboard_redirect')

    parent_prof = get_object_or_404(ParentProfile, user=request.user)
    requirements = TuitionRequirement.objects.filter(parent=parent_prof).order_by('-created_at')
    demos = DemoClass.objects.filter(parent=parent_prof).select_related('tutor__user', 'requirement').order_by('-scheduled_datetime')
    engagements = TuitionEngagement.objects.filter(parent=parent_prof).select_related('tutor__user', 'student').prefetch_related('lessons__record', 'progress_reports')
    students = StudentProfile.objects.filter(parent=parent_prof)

    now = timezone.now()
    engagement_trackers = []
    for eng in engagements:
        lessons = list(eng.lessons.all())
        recorded = [l for l in lessons if hasattr(l, 'record') and l.record]
        if recorded:
            present_or_late = [l for l in recorded if l.record.attendance in [LessonRecord.Attendance.PRESENT, LessonRecord.Attendance.LATE]]
            attendance_pct = round((len(present_or_late) / len(recorded)) * 100)
            absences_count = len([l for l in recorded if l.record.attendance == LessonRecord.Attendance.ABSENT])
        else:
            attendance_pct = 100
            absences_count = 0

        # Upcoming scheduled lessons
        upcoming = [l for l in lessons if l.scheduled_datetime >= now and l.status == LessonSchedule.Status.SCHEDULED]
        upcoming.sort(key=lambda x: x.scheduled_datetime)
        next_lesson = upcoming[0] if upcoming else None

        # Latest progress report
        reports = sorted(list(eng.progress_reports.all()), key=lambda r: r.created_at, reverse=True)
        latest_report = reports[0] if reports else None

        engagement_trackers.append({
            'engagement': eng,
            'attendance_pct': attendance_pct,
            'absences_count': absences_count,
            'total_conducted': max(eng.total_classes_conducted, len(recorded)),
            'recorded_count': len(recorded),
            'next_lesson': next_lesson,
            'upcoming_lessons': upcoming[:3],
            'latest_report': latest_report,
            'all_reports_count': len(reports),
        })

    context = {
        'parent': parent_prof,
        'requirements': requirements,
        'demos': demos,
        'engagements': engagements,
        'engagement_trackers': engagement_trackers,
        'students': students,
    }
    return render(request, 'parents/dashboard.html', context)

@login_required
def requirements_list_view(request):
    if not request.user.is_parent:
        return redirect('accounts:dashboard_redirect')

    parent_prof = get_object_or_404(ParentProfile, user=request.user)

    # Action to close/re-open requirement
    if request.method == 'POST':
        req_id = request.POST.get('requirement_id')
        new_status = request.POST.get('status')
        req = get_object_or_404(TuitionRequirement, pk=req_id, parent=parent_prof)
        if new_status in [TuitionRequirement.Status.CLOSED, TuitionRequirement.Status.OPEN]:
            req.status = new_status
            req.save()
            messages.success(request, f"Requirement {req.lead_id} status updated to {req.get_status_display()}.")
        return redirect('parents:requirements')

    requirements = TuitionRequirement.objects.filter(parent=parent_prof).prefetch_related('applications__tutor', 'matched_tutors__tutor')
    return render(request, 'parents/requirements_list.html', {'requirements': requirements})

@login_required
def matches_view(request, lead_id):
    """View smart matched tutors for a specific tuition requirement."""
    if not request.user.is_parent:
        return redirect('accounts:dashboard_redirect')

    parent_prof = get_object_or_404(ParentProfile, user=request.user)
    requirement = get_object_or_404(TuitionRequirement, lead_id=lead_id, parent=parent_prof)
    matches = TutorMatch.objects.filter(
        requirement=requirement
    ).select_related('tutor__user').prefetch_related(
        'tutor__subjects',
        'tutor__qualifications',
        'tutor__availabilities'
    ).order_by('-match_score')
    applications = LeadApplication.objects.filter(requirement=requirement).select_related('tutor__user')

    # Action to invite tutor
    if request.method == 'POST' and request.POST.get('action') == 'invite':
        tutor_id = request.POST.get('tutor_id')
        tutor = get_object_or_404(TutorProfile, pk=tutor_id)
        match_obj = TutorMatch.objects.filter(requirement=requirement, tutor=tutor).first()
        if match_obj:
            match_obj.is_invited = True
            match_obj.save()

        Notification.objects.create(
            user=tutor.user,
            title="Direct Parent Invitation for Tuition",
            message=f"Parent {parent_prof.display_name} has personally invited you to apply for tuition requirement [{requirement.lead_id}].",
            notification_type=Notification.Type.APPLICATION_ALERT,
            action_url=f"/leads/{requirement.lead_id}/"
        )
        messages.success(request, f"Invitation sent to {tutor.display_name}!")
        return redirect('parents:matches', lead_id=lead_id)

    # Prepare structured tutor comparison and availability data for JavaScript
    tutors_data = []
    for m in matches:
        t = m.tutor
        # Proximity calculation
        req_locality = (requirement.locality or '').strip().lower()
        tutor_locality = (t.primary_locality or '').strip().lower()
        req_city = (requirement.city or '').strip().lower()
        tutor_city = (t.primary_city or '').strip().lower()

        if tutor_locality and req_locality and tutor_locality == req_locality:
            distance_str = f"< 2 km (Same Locality - {t.primary_locality})"
            distance_badge = "Same Locality (<2 km)"
        elif tutor_city and req_city and tutor_city == req_city:
            distance_str = f"~3-5 km ({t.primary_locality} to {requirement.locality})"
            distance_badge = f"Within {requirement.city}"
        else:
            distance_str = f"{t.primary_city} (Online / Remote)"
            distance_badge = "Online / Remote"

        quals = [f"{q.degree_name} ({q.institution})" for q in t.qualifications.all()]
        subjects_list = [s.subject_name for s in t.subjects.all()]
        active_slots = [
            {
                'day': a.get_day_of_week_display(),
                'slot': a.get_slot_display(),
                'day_num': a.day_of_week,
                'slot_code': a.slot,
                'label': f"{a.get_day_of_week_display()[:3]} — {a.get_slot_display().split('(')[0].strip()}"
            }
            for a in t.availabilities.filter(is_active=True)
        ]

        tutors_data.append({
            'id': t.id,
            'name': t.display_name,
            'initial': t.display_name[:1].upper() if t.display_name else 'T',
            'headline': t.headline or 'Dedicated Professional Educator',
            'match_score': m.match_score,
            'match_reasons': m.match_reasons or '',
            'monthly_fee': float(t.monthly_rate_estimate or 0),
            'hourly_fee': float(t.hourly_rate or 0),
            'experience_years': t.experience_years,
            'qualifications': quals or [t.highest_qualification or 'Verified Graduate'],
            'highest_qualification': t.highest_qualification or 'Verified Degree',
            'subjects': subjects_list or [requirement.subjects],
            'locality': t.primary_locality or '',
            'city': t.primary_city or '',
            'service_radius_km': t.service_radius_km,
            'distance_str': distance_str,
            'distance_badge': distance_badge,
            'rating': float(t.average_rating or 5.0),
            'reviews_count': t.total_reviews,
            'ranking_badge': t.ranking_badge,
            'is_fast_responder': t.is_fast_responder,
            'average_response_time_minutes': t.average_response_time_minutes,
            'is_verified': t.is_verified,
            'availabilities': active_slots,
            'profile_url': f"/tutors/{t.id}/",
        })

    context = {
        'parent': parent_prof,
        'requirement': requirement,
        'matches': matches,
        'applications': applications,
        'tutors_json': json.dumps(tutors_data),
    }
    return render(request, 'parents/matches.html', context)

@login_required
@require_POST
def instant_demo_booking_view(request):
    """
    Handles 1-click Instant Demo booking from Tutor cards or Comparison modal.
    Auto-fills requirement context, selects available slot from TutorAvailability,
    and dispatches instant notifications.
    """
    if not request.user.is_parent:
        return redirect('accounts:dashboard_redirect')

    parent_prof = get_object_or_404(ParentProfile, user=request.user)
    req_id = request.POST.get('requirement_id')
    tutor_id = request.POST.get('tutor_id')
    scheduled_datetime_str = request.POST.get('scheduled_datetime')
    demo_mode = request.POST.get('mode', DemoClass.Mode.ONLINE)
    tutor_notes = request.POST.get('tutor_notes', '').strip()
    address = request.POST.get('address', '').strip()

    requirement = get_object_or_404(TuitionRequirement, lead_id=req_id, parent=parent_prof)
    tutor = get_object_or_404(TutorProfile, pk=tutor_id)

    sched_dt = None
    if scheduled_datetime_str:
        try:
            from django.utils.dateparse import parse_datetime
            sched_dt = parse_datetime(scheduled_datetime_str)
            if sched_dt and timezone.is_naive(sched_dt):
                sched_dt = timezone.make_aware(sched_dt)
        except Exception:
            sched_dt = None

    if not sched_dt:
        # Fallback to tomorrow 5:00 PM
        tomorrow = timezone.now().date() + timezone.timedelta(days=1)
        sched_dt = timezone.make_aware(timezone.datetime.combine(tomorrow, timezone.datetime.min.time().replace(hour=17, minute=0)))

    if demo_mode == DemoClass.Mode.HOME and not address:
        address = parent_prof.address_line or f"{parent_prof.locality}, {parent_prof.city}"

    demo = DemoClass.objects.create(
        requirement=requirement,
        tutor=tutor,
        parent=parent_prof,
        mode=demo_mode,
        scheduled_datetime=sched_dt,
        duration_minutes=45,
        address=address,
        status=DemoClass.Status.REQUESTED,
        tutor_notes=tutor_notes or f"Instant Demo requested for {requirement.student_class} ({requirement.subjects})."
    )

    # Sync Tutor Pipeline to DEMO_SCHEDULED
    TutorPipelineCard.objects.update_or_create(
        tutor=tutor,
        requirement=requirement,
        defaults={'stage': TutorPipelineCard.Stage.DEMO_SCHEDULED}
    )

    # Notify tutor
    Notification.objects.create(
        user=tutor.user,
        title="⚡ Instant Demo Booking Request!",
        message=f"Parent {parent_prof.display_name} requested an Instant Demo for {requirement.subjects} ({requirement.student_class}) on {demo.scheduled_datetime.strftime('%b %d, %Y at %I:%M %p')}.",
        notification_type=Notification.Type.DEMO_ALERT,
        action_url="/tutors/demos/"
    )

    messages.success(
        request,
        f"Instant Demo request sent to {tutor.display_name} for {demo.scheduled_datetime.strftime('%A, %b %d at %I:%M %p')}! The educator will confirm shortly."
    )
    return redirect('parents:demos')

@login_required
def progress_report_detail_view(request, report_id):
    """
    Dedicated view displaying a comprehensive student academic progress report card
    with evaluation scores, curriculum topics, strengths, areas for growth, and tutor recommendations.
    """
    if not request.user.is_parent:
        return redirect('accounts:dashboard_redirect')

    parent_prof = get_object_or_404(ParentProfile, user=request.user)
    report = get_object_or_404(StudentProgressReport, pk=report_id, engagement__parent=parent_prof)
    engagement = report.engagement

    return render(request, 'parents/progress_report_detail.html', {
        'report': report,
        'engagement': engagement,
        'student': engagement.student or parent_prof.students.first(),
        'parent': parent_prof,
        'tutor': engagement.tutor,
    })

@login_required
def demos_list_view(request):
    if not request.user.is_parent:
        return redirect('accounts:dashboard_redirect')

    parent_prof = get_object_or_404(ParentProfile, user=request.user)

    if request.method == 'POST':
        demo_id = request.POST.get('demo_id')
        action = request.POST.get('action')
        feedback = request.POST.get('feedback', '')
        demo = get_object_or_404(DemoClass, pk=demo_id, parent=parent_prof)

        if action == 'confirm':
            demo.status = DemoClass.Status.CONFIRMED
            demo.save()
            messages.success(request, "Demo class confirmed!")
        elif action == 'complete':
            demo.status = DemoClass.Status.COMPLETED
            demo.parent_feedback = feedback
            demo.attendance_confirmed_by_parent = True
            demo.is_parent_satisfied = True
            demo.save()
            messages.success(request, "Demo marked as completed and feedback recorded.")
        elif action == 'cancel':
            demo.status = DemoClass.Status.CANCELLED
            demo.save()
            messages.info(request, "Demo cancelled.")
        return redirect('parents:demos')

    demos = DemoClass.objects.filter(parent=parent_prof).select_related('tutor__user', 'requirement')
    return render(request, 'parents/demos_list.html', {'demos': demos})

@login_required
def tuitions_list_view(request):
    """View active tuitions, lessons, progress, and review submissions."""
    if not request.user.is_parent:
        return redirect('accounts:dashboard_redirect')

    parent_prof = get_object_or_404(ParentProfile, user=request.user)

    # Review submission handling
    if request.method == 'POST' and request.POST.get('action') == 'review':
        tutor_id = request.POST.get('tutor_id')
        eng_id = request.POST.get('engagement_id')
        rating = int(request.POST.get('rating', 5) or 5)
        title = request.POST.get('title', 'Great Educator').strip()
        comment = request.POST.get('comment', '').strip()

        tutor = get_object_or_404(TutorProfile, pk=tutor_id)
        eng = get_object_or_404(TuitionEngagement, pk=eng_id, parent=parent_prof) if eng_id else None

        Review.objects.create(
            tutor=tutor,
            parent=parent_prof,
            engagement=eng,
            rating=rating,
            title=title,
            comment=comment
        )
        messages.success(request, f"Review submitted for {tutor.display_name}! Thank you for your feedback.")
        return redirect('parents:tuitions')

    engagements = TuitionEngagement.objects.filter(parent=parent_prof).select_related('tutor__user', 'student').prefetch_related('lessons__record', 'progress_reports')
    return render(request, 'parents/tuitions_list.html', {'engagements': engagements})

@login_required
def confirm_tuition_view(request, lead_id):
    """
    Parent confirms the tuition with selected tutor:
    - Creates TuitionEngagement
    - Automatically executes the Commission Engine if enabled
    - Updates requirement status to CONFIRMED
    - Notifies tutor
    """
    if not request.user.is_parent:
        return redirect('accounts:dashboard_redirect')

    parent_prof = get_object_or_404(ParentProfile, user=request.user)
    requirement = get_object_or_404(TuitionRequirement, lead_id=lead_id, parent=parent_prof)

    if request.method == 'POST':
        tutor_id = request.POST.get('tutor_id')
        agreed_fee = Decimal(request.POST.get('agreed_fee', requirement.budget_amount) or requirement.budget_amount)
        schedule = request.POST.get('schedule_summary', requirement.preferred_timing)
        start_date = request.POST.get('start_date') or timezone.now().date()

        tutor = get_object_or_404(TutorProfile, pk=tutor_id)

        # Create confirmed engagement
        eng, created = TuitionEngagement.objects.get_or_create(
            requirement=requirement,
            tutor=tutor,
            parent=parent_prof,
            defaults={
                'student': requirement.student,
                'agreed_subjects': requirement.subjects,
                'agreed_fee': agreed_fee,
                'schedule_summary': schedule,
                'start_date': start_date,
                'status': TuitionEngagement.Status.ACTIVE
            }
        )

        requirement.status = TuitionRequirement.Status.CONFIRMED
        requirement.save(update_fields=['status'])

        # Trigger Commission Engine
        comm_success, comm_record, comm_msg = generate_commission_for_engagement(eng)

        Notification.objects.create(
            user=tutor.user,
            title="Tuition Confirmed by Parent!",
            message=f"Parent {parent_prof.display_name} has officially confirmed the tuition engagement for [{requirement.lead_id}]. Agreed fee: {agreed_fee}/month.",
            notification_type=Notification.Type.CONFIRMATION_ALERT,
            action_url="/tutors/engagements/"
        )

        messages.success(request, f"Tuition confirmed with {tutor.display_name}! You can now track classes and progress.")
        return redirect('parents:tuitions')

    # Candidate tutors (tutors who unlocked or applied or had a demo)
    unlocked_tutors = TutorProfile.objects.filter(
        unlocked_leads__requirement=requirement
    ).distinct()

    return render(request, 'parents/confirm_tuition.html', {
        'requirement': requirement,
        'unlocked_tutors': unlocked_tutors,
    })

@login_required
def students_manage_view(request):
    if not request.user.is_parent:
        return redirect('accounts:dashboard_redirect')

    parent_prof = get_object_or_404(ParentProfile, user=request.user)

    if request.method == 'POST':
        sname = request.POST.get('student_name', '').strip()
        grade = request.POST.get('grade_level', '').strip()
        school = request.POST.get('school_or_college', '').strip()
        board = request.POST.get('board_curriculum', 'CBSE').strip()
        goals = request.POST.get('academic_goals', '').strip()

        if sname and grade:
            StudentProfile.objects.create(
                parent=parent_prof,
                student_name=sname,
                grade_level=grade,
                school_or_college=school,
                board_curriculum=board,
                academic_goals=goals
            )
            messages.success(request, f"Student profile for '{sname}' added.")
        return redirect('parents:students')

    students = StudentProfile.objects.filter(parent=parent_prof)
    return render(request, 'parents/students_manage.html', {'students': students})
