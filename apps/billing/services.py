from decimal import Decimal
from typing import Optional, Tuple
from django.db import transaction
from django.utils import timezone
from apps.core.models import CompanySettings
from apps.billing.models import CommissionRule, CommissionRecord, Invoice, InvoiceLineItem
from apps.engagements.models import TuitionEngagement
from apps.communication.models import Notification

def generate_commission_for_engagement(engagement: TuitionEngagement) -> Tuple[bool, Optional[CommissionRecord], str]:
    """
    Applies commission policy to a confirmed tuition engagement:
    - Checks global switch company.commission_enabled
    - If disabled, returns early (no records created)
    - If enabled, checks for existing commission to ensure idempotency
    - Calculates amount, taxes, and creates pending CommissionRecord
    - Creates corresponding Invoice for the tutor
    - Alerts the tutor with transparent breakdown
    """
    company = CompanySettings.get_settings()
    if not company.commission_enabled:
        return False, None, "Platform commission is currently disabled in system settings (Model A - Direct settlement)."

    # Idempotency check: don't charge twice
    existing = CommissionRecord.objects.filter(engagement=engagement).first()
    if existing:
        return True, existing, "Commission record already exists for this engagement."

    rule = CommissionRule.get_active_rule()
    if not rule or rule.model_type == CommissionRule.ModelType.NO_COMMISSION:
        return False, None, "No active commission rule configured."

    agreed_fee = engagement.agreed_fee or Decimal('5000.00')
    base_comm, tax_amt, total_due = rule.calculate_commission(agreed_fee)

    if total_due <= Decimal('0.00'):
        return False, None, "Calculated commission is zero."

    with transaction.atomic():
        record = CommissionRecord.objects.create(
            engagement=engagement,
            tutor=engagement.tutor,
            requirement=engagement.requirement,
            rule_applied=rule,
            billing_period=f"{rule.get_model_type_display()} - {timezone.now().strftime('%B %Y')}",
            base_tuition_fee=agreed_fee,
            rate_applied=rule.rate_percentage if rule.calculation_type == CommissionRule.CalculationType.PERCENTAGE else Decimal('0.00'),
            commission_amount=base_comm,
            tax_amount=tax_amt,
            total_amount=total_due,
            status=CommissionRecord.Status.PENDING
        )

        # Generate official Invoice for the tutor
        invoice = Invoice.objects.create(
            user=engagement.tutor.user,
            invoice_type=Invoice.InvoiceType.COMMISSION,
            subtotal=base_comm,
            tax_amount=tax_amt,
            total_amount=total_due,
            status=Invoice.Status.ISSUED,
            due_date=timezone.now().date() + timezone.timedelta(days=7)
        )

        InvoiceLineItem.objects.create(
            invoice=invoice,
            description=f"Platform Service Commission for Confirmed Tuition [{engagement.engagement_id}] - {engagement.requirement.title[:60]}",
            quantity=1,
            unit_price=base_comm,
            total_price=base_comm
        )

        if tax_amt > Decimal('0.00'):
            InvoiceLineItem.objects.create(
                invoice=invoice,
                description=f"{company.tax_name} ({company.tax_percentage}%)",
                quantity=1,
                unit_price=tax_amt,
                total_price=tax_amt
            )

        # Alert the tutor
        try:
            Notification.objects.create(
                user=engagement.tutor.user,
                title=f"Tuition Confirmation & Commission Invoice Generated",
                message=f"Congratulations on confirming tuition engagement {engagement.engagement_id}! Platform commission of {company.currency_symbol}{total_due} has been invoiced (Due in 7 days).",
                notification_type=Notification.Type.COMMISSION_ALERT,
                action_url="/tutor/billing/"
            )
        except Exception:
            pass

    return True, record, "Commission calculated and invoiced successfully."
