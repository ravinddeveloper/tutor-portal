from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.accounts.models import User
from apps.parents.models import ParentProfile
from apps.tutors.models import TutorProfile
from apps.billing.models import ContactCreditWallet, CreditTransaction
from apps.core.models import CompanySettings

def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Allow login by username or email
        user = authenticate(request, username=identifier, password=password)
        if not user:
            try:
                user_obj = User.objects.get(email__iexact=identifier)
                user = authenticate(request, username=user_obj.username, password=password)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                user = None

        if user:
            login(request, user)
            messages.success(request, f"Welcome back, {user.display_name}!")
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('accounts:dashboard_redirect')
        else:
            messages.error(request, "Invalid username/email or password.")

    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, "You have been securely signed out.")
    return redirect('core:home')

def register_parent_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        city = request.POST.get('city', 'Bengaluru').strip()
        locality = request.POST.get('locality', '').strip()

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "An account with this email address already exists.")
            return render(request, 'accounts/register_parent.html')

        # Split full name into first and last name
        parts = full_name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''
        username = f"parent_{email.split('@')[0]}"

        # Ensure unique username
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=User.Role.PARENT,
            phone_number=phone,
            city=city,
            locality=locality,
            is_phone_verified=True,
            is_email_verified=True
        )

        ParentProfile.objects.create(
            user=user,
            city=city,
            locality=locality,
            alternate_phone=phone
        )

        login(request, user)
        messages.success(request, "Account created successfully! Welcome to the Parent Portal.")
        return redirect('parents:dashboard')

    return render(request, 'accounts/register_parent.html')

def register_tutor_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        city = request.POST.get('city', 'Bengaluru').strip()
        locality = request.POST.get('locality', '').strip()
        headline = request.POST.get('headline', '').strip()
        qualification = request.POST.get('qualification', 'Bachelor Degree').strip()
        teaching_mode = request.POST.get('teaching_mode', TutorProfile.TeachingMode.BOTH_HOME_ONLINE)

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "An account with this email address already exists.")
            return render(request, 'accounts/register_tutor.html')

        parts = full_name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''
        username = f"tutor_{email.split('@')[0]}"

        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=User.Role.TUTOR,
            phone_number=phone,
            city=city,
            locality=locality,
            is_phone_verified=True,
            is_email_verified=True
        )

        tprofile = TutorProfile.objects.create(
            user=user,
            headline=headline or f"Experienced Educator in {city}",
            highest_qualification=qualification,
            primary_city=city,
            primary_locality=locality,
            teaching_mode=teaching_mode,
            verification_status=TutorProfile.VerificationStatus.SUBMITTED
        )

        # Award 3 Free Welcome Contact Credits
        wallet = ContactCreditWallet.get_or_create_wallet(tprofile)
        wallet.free_credits = 3
        wallet.save()

        CreditTransaction.objects.create(
            wallet=wallet,
            transaction_type=CreditTransaction.TransactionType.BONUS_AWARD,
            amount=3,
            balance_after=3,
            reference_note="Welcome Bonus: 3 Free Contact Unlock Credits"
        )

        login(request, user)
        messages.success(request, "Welcome! Your tutor profile is submitted and 3 Free Welcome Credits have been added to your wallet.")
        return redirect('tutors:dashboard')

    return render(request, 'accounts/register_tutor.html')

@login_required
def dashboard_redirect_view(request):
    """Smart router directing users to their dedicated dashboard based on role."""
    if request.user.is_super_admin or request.user.is_operations:
        return redirect('custom_admin:dashboard')
    elif request.user.is_tutor:
        return redirect('tutors:dashboard')
    elif request.user.is_parent:
        return redirect('parents:dashboard')
    return redirect('core:home')
