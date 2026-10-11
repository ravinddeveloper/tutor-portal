from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from apps.parents.models import ParentProfile, StudentProfile
from apps.leads.models import TuitionRequirement, TutorMatch, LeadApplication
from apps.engagements.models import DemoClass, TuitionEngagement, Review
from apps.tutors.models import TutorProfile
from apps.billing.services import generate_commission_for_engagement
from apps.communication.models import Notification

@login_required
def dashboard_view(request):
    if not request.user.is_parent:
        return redirect('accounts:dashboard_redirect')

    parent_prof = get_object_or_404(ParentProfile, user=request.user)
    requirements = TuitionRequirement.objects.filter(parent=parent_prof).order_by('-created_at')
    demos = DemoClass.objects.filter(parent=parent_prof).select_related('tutor__user', 'requirement').order_by('-scheduled_datetime')
    engagements = TuitionEngagement.objects.filter(parent=parent_prof).select_related('tutor__user')
    students = StudentProfile.objects.filter(parent=parent_prof)

    context = {
        'parent': parent_prof,
        'requirements': requirements,
        'demos': demos,
        'engagements': engagements,
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
    matches = TutorMatch.objects.filter(requirement=requirement).select_related('tutor__user').prefetch_related('tutor__subjects').order_by('-match_score')
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

    context = {
        'requirement': requirement,
        'matches': matches,
        'applications': applications,
    }
    return render(request, 'parents/matches.html', context)

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
