from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.db.models import Q
from django.core.paginator import Paginator

from apps.accounts.models import User
from apps.parents.models import ParentProfile, StudentProfile
from apps.leads.models import TuitionRequirement, TutorMatch, LeadUnlock, LeadApplication
from apps.leads.matching import run_tutor_matching
from apps.leads.services import unlock_lead_for_tutor
from apps.tutors.models import TutorProfile
from apps.billing.models import ContactCreditWallet

def post_requirement_view(request):
    """
    Guided wizard for posting tuition requirements:
    - Collects subjects, class, curriculum, location, schedule, budget
    - Collects confidential parent contact info (hidden until unlocked)
    - If user not logged in, creates parent account and auto-authenticates
    - Runs intelligent tutor matching immediately
    - Redirects to the match recommendation confirmation screen
    """
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        student_class = request.POST.get('student_class', 'Class 10').strip()
        board = request.POST.get('board_curriculum', 'CBSE').strip()
        subjects = request.POST.get('subjects', '').strip()
        tuition_type = request.POST.get('tuition_type', TuitionRequirement.TuitionType.HOME_TUITION)
        city = request.POST.get('city', 'Bengaluru').strip()
        locality = request.POST.get('locality', '').strip()
        landmark = request.POST.get('landmark', '').strip()
        days_per_week = int(request.POST.get('days_per_week', 3) or 3)
        preferred_timing = request.POST.get('preferred_timing', 'Evening (5:00 PM - 7:00 PM)').strip()
        budget = Decimal(request.POST.get('budget_amount', 5000) or 5000)
        gender_pref = request.POST.get('preferred_gender', TuitionRequirement.GenderPreference.ANY)
        learning_goals = request.POST.get('learning_goals', '').strip()

        # Contact Details
        parent_name = request.POST.get('parent_contact_name', '').strip()
        phone = request.POST.get('contact_phone', '').strip()
        email = request.POST.get('contact_email', '').strip()
        full_address = request.POST.get('full_address', '').strip()

        if not title:
            title = f"{tuition_type.replace('_', ' ').title()} for {student_class} ({board}) {subjects} in {locality}"

        # Resolve or create parent profile
        if request.user.is_authenticated and request.user.is_parent:
            parent_prof = request.user.parent_profile
        else:
            # Check or create parent account
            user_obj = User.objects.filter(email__iexact=email).first() if email else None
            if not user_obj:
                username = f"parent_{phone[-6:]}" if phone else f"parent_{city.lower()[:4]}"
                base_u = username
                c = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_u}{c}"
                    c += 1
                user_obj = User.objects.create_user(
                    username=username,
                    email=email or f"{username}@edututorpro.local",
                    first_name=parent_name.split(' ')[0] if parent_name else 'Parent',
                    last_name=parent_name.split(' ')[1] if ' ' in parent_name else '',
                    phone_number=phone,
                    role=User.Role.PARENT,
                    city=city,
                    locality=locality,
                    is_phone_verified=True,
                    is_email_verified=True
                )
                user_obj.set_password('parent123')
                user_obj.save()

            parent_prof, _ = ParentProfile.objects.get_or_create(
                user=user_obj,
                defaults={'city': city, 'locality': locality, 'address_line': full_address}
            )
            # Log them in automatically
            login(request, user_obj)

        # Create requirement
        req = TuitionRequirement.objects.create(
            parent=parent_prof,
            title=title,
            student_class=student_class,
            board_curriculum=board,
            subjects=subjects,
            tuition_type=tuition_type,
            city=city,
            locality=locality,
            landmark=landmark,
            days_per_week=days_per_week,
            preferred_timing=preferred_timing,
            budget_amount=budget,
            preferred_gender=gender_pref,
            learning_goals=learning_goals,
            parent_contact_name=parent_name or parent_prof.display_name,
            contact_phone=phone or user_obj.phone_number,
            contact_email=email or user_obj.email,
            full_address=full_address,
            status=TuitionRequirement.Status.OPEN
        )

        # Run intelligent tutor matching
        matched_tutors = run_tutor_matching(req)

        messages.success(request, f"Tuition requirement {req.lead_id} posted successfully! We found {len(matched_tutors)} matched educators.")
        return redirect('parents:matches', lead_id=req.lead_id)

    return render(request, 'leads/post_requirement.html')

def board_view(request):
    """Public browse board for tuition leads (similar to HomeTutorSite reference)."""
    qs = TuitionRequirement.objects.filter(status=TuitionRequirement.Status.OPEN)

    sub_q = request.GET.get('subject', '').strip()
    if sub_q:
        qs = qs.filter(Q(subjects__icontains=sub_q) | Q(title__icontains=sub_q))

    city_q = request.GET.get('city', '').strip()
    if city_q:
        qs = qs.filter(Q(city__icontains=city_q) | Q(locality__icontains=city_q))

    type_q = request.GET.get('tuition_type', '').strip()
    if type_q:
        qs = qs.filter(tuition_type=type_q)

    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page')
    leads_page = paginator.get_page(page_number)

    context = {
        'leads': leads_page,
        'sub_q': sub_q,
        'city_q': city_q,
        'type_q': type_q,
        'total_count': paginator.count,
    }
    return render(request, 'leads/board.html', context)

def detail_view(request, lead_id):
    """Tuition lead detail view with contact privacy and unlock actions."""
    lead = get_object_or_404(
        TuitionRequirement.objects.select_related('parent__user').prefetch_related('matched_tutors__tutor'),
        lead_id=lead_id
    )

    # Increment view counter
    lead.total_views += 1
    lead.save(update_fields=['total_views'])

    is_unlocked = False
    match_info = None

    if request.user.is_authenticated and request.user.is_tutor:
        tprofile = getattr(request.user, 'tutor_profile', None)
        if tprofile:
            is_unlocked = lead.is_unlocked_by(tprofile)
            match_info = TutorMatch.objects.filter(requirement=lead, tutor=tprofile).first()

            # Handle Unlock Action
            if request.method == 'POST' and request.POST.get('action') == 'unlock':
                success, msg, data = unlock_lead_for_tutor(lead, tprofile)
                if success:
                    messages.success(request, msg)
                    return redirect('leads:detail', lead_id=lead.lead_id)
                else:
                    messages.error(request, msg)

            # Handle Proposal Application Action
            if request.method == 'POST' and request.POST.get('action') == 'apply':
                note = request.POST.get('cover_note', '').strip()
                fee = Decimal(request.POST.get('proposed_fee', lead.budget_amount) or lead.budget_amount)
                LeadApplication.objects.update_or_create(
                    requirement=lead,
                    tutor=tprofile,
                    defaults={'cover_note': note, 'proposed_fee': fee, 'status': LeadApplication.Status.PENDING}
                )
                lead.total_applications += 1
                lead.save(update_fields=['total_applications'])
                messages.success(request, "Your tuition proposal has been submitted to the parent!")
                return redirect('leads:detail', lead_id=lead.lead_id)

    context = {
        'lead': lead,
        'is_unlocked': is_unlocked,
        'match_info': match_info,
    }
    return render(request, 'leads/detail.html', context)
