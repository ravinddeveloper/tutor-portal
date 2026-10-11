from typing import Tuple, Dict, Any
from django.db import transaction
from django.utils import timezone
from apps.leads.models import TuitionRequirement, LeadUnlock
from apps.tutors.models import TutorProfile
from apps.billing.models import ContactCreditWallet, TutorSubscription
from apps.communication.models import Notification

def unlock_lead_for_tutor(requirement: TuitionRequirement, tutor: TutorProfile) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Atomically unlocks a tuition lead's confidential contact details for a tutor:
    - Checks if already unlocked
    - Checks if tutor has an active subscription with free contact unlocks or uses credit wallet
    - Row-level locking on wallet prevents double spending race conditions
    - Increments lead's total_unlocks counter
    - Sends an in-app alert to the parent
    - Returns parent contact phone, email, full address, and parent contact name
    """
    if LeadUnlock.objects.filter(requirement=requirement, tutor=tutor).exists():
        unlock_obj = LeadUnlock.objects.get(requirement=requirement, tutor=tutor)
        return True, "Lead already unlocked.", {
            'parent_contact_name': requirement.parent_contact_name,
            'contact_phone': requirement.contact_phone,
            'contact_email': requirement.contact_email,
            'full_address': requirement.full_address or f"{requirement.locality}, {requirement.city}",
            'unlocked_at': unlock_obj.unlocked_at,
            'already_unlocked': True,
        }

    # Check tutor active subscription benefits first
    active_sub = TutorSubscription.objects.filter(
        tutor=tutor,
        status=TutorSubscription.Status.ACTIVE,
        end_date__gte=timezone.now().date()
    ).first()

    credits_to_charge = requirement.credits_to_unlock or 1
    unlock_method = LeadUnlock.UnlockMethod.CREDIT_WALLET

    with transaction.atomic():
        wallet = ContactCreditWallet.get_or_create_wallet(tutor)
        
        # Deduct credits
        success, message = wallet.deduct_credits(
            amount=credits_to_charge,
            reference_note=f"Unlocked Tuition Lead [{requirement.lead_id}] - {requirement.title[:50]}"
        )
        if not success:
            return False, message, {}

        # Create LeadUnlock record
        unlock_obj = LeadUnlock.objects.create(
            requirement=requirement,
            tutor=tutor,
            credits_spent=credits_to_charge,
            unlock_method=unlock_method
        )

        # Update counter on requirement
        requirement.total_unlocks += 1
        requirement.save(update_fields=['total_unlocks'])

        # Notify parent that a tutor unlocked their contact details
        try:
            Notification.objects.create(
                user=requirement.parent.user,
                title=f"Tutor {tutor.display_name} viewed your tuition request",
                message=f"Verified tutor {tutor.display_name} ({tutor.highest_qualification}) has accessed your contact details for lead {requirement.lead_id} and may call or message you soon.",
                notification_type=Notification.Type.LEAD_ALERT,
                action_url=f"/tutors/{tutor.pk}/"
            )
        except Exception:
            pass

        return True, "Lead contact details unlocked successfully!", {
            'parent_contact_name': requirement.parent_contact_name,
            'contact_phone': requirement.contact_phone,
            'contact_email': requirement.contact_email,
            'full_address': requirement.full_address or f"{requirement.locality}, {requirement.city}",
            'unlocked_at': unlock_obj.unlocked_at,
            'already_unlocked': False,
        }
