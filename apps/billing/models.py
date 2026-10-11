import uuid
from decimal import Decimal
from django.db import models, transaction
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.tutors.models import TutorProfile
from apps.leads.models import TuitionRequirement, LeadUnlock
from apps.engagements.models import TuitionEngagement

class CommissionRule(models.Model):
    """Business Rules Engine for Commission Calculation across the marketplace."""
    class ModelType(models.TextChoices):
        NO_COMMISSION = 'NO_COMMISSION', _('Model A: No Commission (Pure Direct Settlement)')
        ONE_TIME = 'ONE_TIME', _('Model B: One-Time Confirmation Fee')
        FIRST_MONTH = 'FIRST_MONTH', _('Model C: First-Month Commission Percentage')
        RECURRING = 'RECURRING', _('Model D: Recurring Monthly Commission')
        PER_SESSION = 'PER_SESSION', _('Model E: Per-Session / Class Commission')
        HYBRID = 'HYBRID', _('Model F: Hybrid (Subscription + Lower Commission)')

    class CalculationType(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', _('Percentage of Tuition Fee')
        FIXED_AMOUNT = 'FIXED', _('Fixed Flat Amount')

    is_active = models.BooleanField(default=True, help_text=_('Is this commission rule currently effective?'))
    rule_name = models.CharField(max_length=150, default='Standard First-Month Commission')
    model_type = models.CharField(max_length=30, choices=ModelType.choices, default=ModelType.FIRST_MONTH)
    calculation_type = models.CharField(max_length=20, choices=CalculationType.choices, default=CalculationType.PERCENTAGE)
    
    rate_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=40.00,
        help_text=_('Commission percentage, e.g. 40.00 for 40% of first month tuition')
    )
    fixed_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_('Fixed amount if fixed calculation is selected')
    )
    minimum_commission = models.DecimalField(max_digits=10, decimal_places=2, default=500.00)
    maximum_commission = models.DecimalField(max_digits=10, decimal_places=2, default=8000.00)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=18.00, help_text=_('GST / VAT percentage applied to commission'))
    
    charged_to = models.CharField(max_length=20, default='TUTOR', help_text=_('TUTOR or PARENT'))
    description = models.TextField(blank=True, default='Platform connects verified tutors with clients and levies a 40% first-month service fee.')
    effective_from = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['-is_active', '-id']

    @classmethod
    def get_active_rule(cls):
        return cls.objects.filter(is_active=True).first()

    def calculate_commission(self, tuition_fee: Decimal):
        """Calculates commission amount and applicable tax based on this rule."""
        if self.model_type == self.ModelType.NO_COMMISSION:
            return Decimal('0.00'), Decimal('0.00'), Decimal('0.00')

        if self.calculation_type == self.CalculationType.FIXED_AMOUNT:
            base_comm = self.fixed_amount
        else:
            base_comm = (tuition_fee * self.rate_percentage) / Decimal('100.00')

        # Apply bounds
        if self.minimum_commission > Decimal('0.00'):
            base_comm = max(base_comm, self.minimum_commission)
        if self.maximum_commission > Decimal('0.00'):
            base_comm = min(base_comm, self.maximum_commission)

        tax_amt = (base_comm * self.tax_percentage) / Decimal('100.00')
        total_due = base_comm + tax_amt
        return round(base_comm, 2), round(tax_amt, 2), round(total_due, 2)

    def __str__(self):
        return f"{self.rule_name} ({self.get_model_type_display()} - {self.rate_percentage}%)"


class CommissionRecord(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending Payment')
        INVOICED = 'INVOICED', _('Invoiced')
        PAID = 'PAID', _('Paid & Settled')
        WAIVED = 'WAIVED', _('Waived by Admin')
        OVERDUE = 'OVERDUE', _('Overdue')
        DISPUTED = 'DISPUTED', _('Disputed')

    record_id = models.CharField(max_length=30, unique=True)
    engagement = models.ForeignKey(TuitionEngagement, on_delete=models.CASCADE, related_name='commission_records')
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='commission_records')
    requirement = models.ForeignKey(TuitionRequirement, on_delete=models.CASCADE, related_name='commission_records')
    rule_applied = models.ForeignKey(CommissionRule, on_delete=models.SET_NULL, null=True, blank=True)
    
    billing_period = models.CharField(max_length=50, default='First Month Commission')
    base_tuition_fee = models.DecimalField(max_digits=10, decimal_places=2)
    rate_applied = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    waiver_reason = models.TextField(blank=True)
    waived_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='waived_commissions')
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.record_id:
            self.record_id = f"COM-{uuid.uuid4().hex[:7].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.record_id}] {self.tutor.display_name} - {self.total_amount} ({self.get_status_display()})"


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    tagline = models.CharField(max_length=200, default='For ambitious educators')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=999.00)
    duration_days = models.PositiveIntegerField(default=30)
    lead_credits_included = models.PositiveIntegerField(default=10)
    free_contact_unlocks = models.PositiveIntegerField(default=5)
    is_featured_badge = models.BooleanField(default=False)
    priority_matching = models.BooleanField(default=False)
    commission_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['sort_order', 'price']

    def __str__(self):
        return f"{self.name} (₹{self.price} / {self.duration_days} days)"


class TutorSubscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        EXPIRED = 'EXPIRED', _('Expired')
        CANCELLED = 'CANCELLED', _('Cancelled')

    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tutor.display_name} - {self.plan.name} ({self.get_status_display()})"


class ContactCreditWallet(models.Model):
    """Credit wallet for tutors with thread-safe atomic deductions."""
    tutor = models.OneToOneField(TutorProfile, on_delete=models.CASCADE, related_name='credit_wallet')
    free_credits = models.PositiveIntegerField(default=2, help_text=_('Welcome or promotional credits'))
    purchased_credits = models.PositiveIntegerField(default=0)
    bonus_credits = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_balance(self):
        return self.free_credits + self.purchased_credits + self.bonus_credits

    @classmethod
    def get_or_create_wallet(cls, tutor_profile):
        wallet, _ = cls.objects.get_or_create(tutor=tutor_profile)
        return wallet

    def deduct_credits(self, amount: int = 1, reference_note: str = 'Lead Contact Unlock', unlock_instance: LeadUnlock = None):
        """Atomically deducts credits prioritizing free -> bonus -> purchased."""
        with transaction.atomic():
            # Lock wallet row
            wallet = ContactCreditWallet.objects.select_for_update().get(pk=self.pk)
            if wallet.total_balance < amount:
                return False, "Insufficient credit balance. Please recharge or upgrade plan."

            remaining_to_deduct = amount

            # 1. Deduct from free
            if wallet.free_credits > 0:
                deduct_free = min(wallet.free_credits, remaining_to_deduct)
                wallet.free_credits -= deduct_free
                remaining_to_deduct -= deduct_free

            # 2. Deduct from bonus
            if remaining_to_deduct > 0 and wallet.bonus_credits > 0:
                deduct_bonus = min(wallet.bonus_credits, remaining_to_deduct)
                wallet.bonus_credits -= deduct_bonus
                remaining_to_deduct -= deduct_bonus

            # 3. Deduct from purchased
            if remaining_to_deduct > 0 and wallet.purchased_credits > 0:
                deduct_purchased = min(wallet.purchased_credits, remaining_to_deduct)
                wallet.purchased_credits -= deduct_purchased
                remaining_to_deduct -= deduct_purchased

            wallet.save()

            CreditTransaction.objects.create(
                wallet=wallet,
                transaction_type=CreditTransaction.TransactionType.LEAD_UNLOCK,
                amount=-amount,
                balance_after=wallet.total_balance,
                reference_note=reference_note,
                lead_unlock=unlock_instance
            )
            return True, "Credits deducted successfully."

    def add_credits(self, amount: int, credit_type: str = 'PURCHASED', reference_note: str = 'Recharge Pack'):
        with transaction.atomic():
            wallet = ContactCreditWallet.objects.select_for_update().get(pk=self.pk)
            if credit_type == 'FREE':
                wallet.free_credits += amount
                tx_type = CreditTransaction.TransactionType.BONUS_AWARD
            elif credit_type == 'BONUS':
                wallet.bonus_credits += amount
                tx_type = CreditTransaction.TransactionType.BONUS_AWARD
            elif credit_type == 'REFUND':
                wallet.bonus_credits += amount
                tx_type = CreditTransaction.TransactionType.REFUND_CREDIT
            else:
                wallet.purchased_credits += amount
                tx_type = CreditTransaction.TransactionType.PURCHASE

            wallet.save()

            CreditTransaction.objects.create(
                wallet=wallet,
                transaction_type=tx_type,
                amount=amount,
                balance_after=wallet.total_balance,
                reference_note=reference_note
            )
            return True

    def __str__(self):
        return f"Wallet ({self.tutor.display_name}): {self.total_balance} Credits"


class CreditTransaction(models.Model):
    class TransactionType(models.TextChoices):
        PURCHASE = 'PURCHASE', _('Purchased Credit Pack')
        BONUS_AWARD = 'BONUS_AWARD', _('Bonus / Referral Award')
        LEAD_UNLOCK = 'LEAD_UNLOCK', _('Lead Contact Unlock')
        REFUND_CREDIT = 'REFUND_CREDIT', _('Refund / Replacement Credit')
        ADMIN_ADJUSTMENT = 'ADMIN_ADJUSTMENT', _('Administrative Adjustment')

    wallet = models.ForeignKey(ContactCreditWallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=30, choices=TransactionType.choices)
    amount = models.IntegerField(help_text=_('Positive for addition, negative for deduction'))
    balance_after = models.PositiveIntegerField()
    reference_note = models.CharField(max_length=255)
    lead_unlock = models.ForeignKey(LeadUnlock, on_delete=models.SET_NULL, null=True, blank=True, related_name='credit_deductions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.wallet.tutor.display_name} | {self.amount:+d} ({self.get_transaction_type_display()})"


class Invoice(models.Model):
    class InvoiceType(models.TextChoices):
        SUBSCRIPTION = 'SUBSCRIPTION', _('Tutor Membership Plan')
        CREDIT_PURCHASE = 'CREDIT_PURCHASE', _('Contact Credit Pack')
        COMMISSION = 'COMMISSION', _('Marketplace Commission')
        TUITION_FEE = 'TUITION_FEE', _('Tuition Session Fee')

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        ISSUED = 'ISSUED', _('Issued')
        PAID = 'PAID', _('Paid')
        CANCELLED = 'CANCELLED', _('Cancelled')
        REFUNDED = 'REFUNDED', _('Refunded')

    invoice_number = models.CharField(max_length=30, unique=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invoices')
    invoice_type = models.CharField(max_length=25, choices=InvoiceType.choices, default=InvoiceType.CREDIT_PURCHASE)
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PAID)
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f"INV-{uuid.uuid4().hex[:7].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number} - {self.user.display_name} (₹{self.total_amount})"


class InvoiceLineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='line_items')
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.description} x{self.quantity} = ₹{self.total_price}"


class Payment(models.Model):
    class Method(models.TextChoices):
        UPI = 'UPI', _('UPI (Instant)')
        CARD = 'CARD', _('Debit / Credit Card')
        NET_BANKING = 'NET_BANKING', _('Net Banking')
        WALLET = 'WALLET', _('Digital Wallet')
        BANK_TRANSFER = 'BANK_TRANSFER', _('NEFT / RTGS Bank Transfer')
        CASH = 'CASH', _('Cash / Direct')

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        SUCCESSFUL = 'SUCCESSFUL', _('Successful')
        FAILED = 'FAILED', _('Failed')
        REFUNDED = 'REFUNDED', _('Refunded')

    payment_id = models.CharField(max_length=30, unique=True, db_index=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.UPI)
    gateway_reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUCCESSFUL)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.payment_id}] ₹{self.amount} by {self.user.display_name} ({self.get_status_display()})"


class Refund(models.Model):
    class Status(models.TextChoices):
        REQUESTED = 'REQUESTED', _('Requested')
        APPROVED = 'APPROVED', _('Approved')
        PROCESSED = 'PROCESSED', _('Processed')
        REJECTED = 'REJECTED', _('Rejected')

    refund_id = models.CharField(max_length=30, unique=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPROVED)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.refund_id:
            self.refund_id = f"REF-{uuid.uuid4().hex[:7].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.refund_id}] ₹{self.amount} ({self.get_status_display()})"
