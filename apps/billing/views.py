import uuid
import json
import datetime
from decimal import Decimal
from typing import Tuple, Dict, Any, Optional

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import transaction

from apps.billing.models import (
    SubscriptionPlan, TutorSubscription, ContactCreditWallet, CreditTransaction,
    Invoice, InvoiceLineItem, Payment, CommissionRecord
)
from apps.tutors.models import TutorProfile
from apps.engagements.models import TuitionEngagement
from apps.core.models import CompanySettings, AuditLog
from apps.communication.models import Notification
from apps.core.emails import send_transactional_email


# Predefined verified coupon codes
PROMO_COUPONS = {
    'WELCOME50': {
        'code': 'WELCOME50',
        'type': 'PERCENT',
        'value': Decimal('50.00'),
        'max_discount': Decimal('500.00'),
        'min_order': Decimal('200.00'),
        'description': '50% off on your order (up to ₹500)',
    },
    'TUTOR20': {
        'code': 'TUTOR20',
        'type': 'PERCENT',
        'value': Decimal('20.00'),
        'max_discount': Decimal('400.00'),
        'min_order': Decimal('300.00'),
        'description': '20% Educator Discount (up to ₹400)',
    },
    'FIRST100': {
        'code': 'FIRST100',
        'type': 'FLAT',
        'value': Decimal('100.00'),
        'max_discount': Decimal('100.00'),
        'min_order': Decimal('250.00'),
        'description': 'Flat ₹100 instant checkout savings',
    },
    'SUPER10': {
        'code': 'SUPER10',
        'type': 'PERCENT',
        'value': Decimal('10.00'),
        'max_discount': Decimal('1000.00'),
        'min_order': Decimal('500.00'),
        'description': '10% sitewide special discount',
    },
}


def calculate_discount(coupon_code: str, base_amount: Decimal) -> Tuple[Decimal, Optional[str], Optional[str]]:
    """Calculates discount amount for a given coupon code and base order amount."""
    if not coupon_code:
        return Decimal('0.00'), None, None

    code_upper = coupon_code.strip().upper()
    coupon = PROMO_COUPONS.get(code_upper)
    if not coupon:
        return Decimal('0.00'), None, f"Invalid or expired coupon code: '{coupon_code}'"

    min_order = coupon.get('min_order', Decimal('0.00'))
    if base_amount < min_order:
        return Decimal('0.00'), None, f"Coupon '{code_upper}' requires a minimum order of ₹{min_order}."

    if coupon['type'] == 'PERCENT':
        discount = (base_amount * coupon['value']) / Decimal('100.00')
        max_disc = coupon.get('max_discount')
        if max_disc and discount > max_disc:
            discount = max_disc
    else:  # FLAT
        discount = min(coupon['value'], base_amount)

    discount = round(discount, 2)
    return discount, coupon['description'], None


@login_required
def checkout_view(request):
    """
    Dedicated, state-of-the-art Payment & Checkout Gateway Page.
    Handles multiple transaction categories:
    - 'plan': Tutor Subscription Membership Plan
    - 'credits': Contact Credit Pack
    - 'commission': Marketplace Commission Invoice Settlement
    - 'invoice': Direct Tax Invoice payment
    - 'tuition_fee': Parent-to-tutor engagement payment
    """
    company = CompanySettings.get_settings()
    checkout_type = request.GET.get('type', 'plan')
    coupon_code = request.GET.get('coupon', '').strip().upper()

    item_title = ""
    item_subtitle = ""
    item_category_badge = "Order Summary"
    base_price = Decimal('0.00')
    features = []
    metadata = {}
    plan_obj = None
    commission_obj = None
    invoice_obj = None

    if checkout_type == 'plan':
        plan_id = request.GET.get('id')
        if plan_id:
            plan_obj = get_object_or_404(SubscriptionPlan, pk=plan_id, is_active=True)
        else:
            plan_obj = SubscriptionPlan.objects.filter(is_active=True).first()
            if not plan_obj:
                messages.error(request, "No active membership plans available at this moment.")
                return redirect('core:pricing')

        if not request.user.is_tutor and not request.user.is_super_admin:
            messages.warning(request, "Educator membership plans are designed for registered tutors.")

        item_title = f"{plan_obj.name} Educator Plan"
        item_subtitle = f"Full access & priority visibility for {plan_obj.duration_days} days"
        item_category_badge = "Membership Subscription"
        base_price = plan_obj.price
        features = [
            f"{plan_obj.lead_credits_included} Verified Parent Contact Credits included",
            f"{plan_obj.free_contact_unlocks} Instant Priority Lead matches",
            "Featured badge on public directory listing" if plan_obj.is_featured_badge else "Verified tutor badge",
            "AI Priority Matching Engine boost" if plan_obj.priority_matching else "Standard matching priority",
            "Direct in-app messaging & SMS lead notifications",
        ]
        metadata['plan_id'] = plan_obj.id

    elif checkout_type == 'credits':
        if not request.user.is_tutor and not request.user.is_super_admin:
            messages.warning(request, "Contact credits are for verified tutors to unlock parent phone numbers.")

        credits_count = int(request.GET.get('credits', 15))
        default_prices = {5: Decimal('299.00'), 15: Decimal('699.00'), 30: Decimal('1299.00'), 50: Decimal('1999.00')}
        req_amount = request.GET.get('amount')
        base_price = Decimal(req_amount) if req_amount else default_prices.get(credits_count, Decimal('699.00'))

        item_title = f"Contact Credit Pack: {credits_count} Credits"
        item_subtitle = "1 Credit = 1 Verified Parent Contact & Address Unlock"
        item_category_badge = "Credit Recharge Pack"
        features = [
            f"{credits_count} Verified Parent Phone & WhatsApp contact unlocks",
            "Credits never expire — use anytime at your pace",
            "100% replacement guarantee if contact is unreachable or invalid",
            "Instant wallet credit balance update upon payment confirmation",
        ]
        metadata['credits_count'] = credits_count

    elif checkout_type == 'commission':
        comm_id = request.GET.get('id')
        commission_obj = get_object_or_404(CommissionRecord, pk=comm_id)
        if commission_obj.tutor.user != request.user and not (request.user.is_super_admin or request.user.is_operations):
            messages.error(request, "Unauthorized to settle this commission invoice.")
            return redirect('tutors:billing')

        if commission_obj.status == CommissionRecord.Status.PAID:
            messages.info(request, f"Commission invoice {commission_obj.record_id} has already been paid and settled.")
            return redirect('tutors:billing')

        item_title = f"Commission Settlement: {commission_obj.record_id}"
        item_subtitle = f"Confirmed tuition: {commission_obj.requirement.title[:65]}"
        item_category_badge = "Tuition Commission"
        base_price = commission_obj.commission_amount
        features = [
            f"Tuition Engagement Ref: {commission_obj.engagement.engagement_id}",
            f"Agreed Tuition Fee: {company.currency_symbol}{commission_obj.base_tuition_fee}",
            f"Commission Rate Applied: {commission_obj.rate_applied}%",
            f"Tax ({company.tax_name} {company.tax_percentage}%): {company.currency_symbol}{commission_obj.tax_amount}",
            "Instant digital clearance and tax invoice issued",
        ]
        metadata['commission_id'] = commission_obj.id

    elif checkout_type == 'invoice':
        inv_num = request.GET.get('number')
        invoice_obj = get_object_or_404(Invoice, invoice_number=inv_num)
        if invoice_obj.user != request.user and not (request.user.is_super_admin or request.user.is_operations):
            messages.error(request, "Unauthorized to access this invoice.")
            return redirect('core:home')

        if invoice_obj.status == Invoice.Status.PAID:
            messages.info(request, f"Invoice {invoice_obj.invoice_number} is already paid.")
            return redirect('billing:invoice_detail', invoice_number=invoice_obj.invoice_number)

        item_title = f"Tax Invoice Settlement #{invoice_obj.invoice_number}"
        item_subtitle = f"Issued on {invoice_obj.created_at.strftime('%d %b %Y')}"
        item_category_badge = "Official Tax Invoice"
        base_price = invoice_obj.subtotal
        features = [item.description for item in invoice_obj.line_items.all()][:4]
        metadata['invoice_number'] = invoice_obj.invoice_number

    elif checkout_type == 'tuition_fee':
        eng_id = request.GET.get('engagement_id')
        eng = get_object_or_404(TuitionEngagement, pk=eng_id)
        fee_amt = Decimal(request.GET.get('amount', eng.agreed_fee or '5000.00'))
        item_title = f"Tuition Fee: {eng.engagement_id}"
        item_subtitle = f"Subject: {eng.agreed_subjects} | Tutor: {eng.tutor.display_name}"
        item_category_badge = "Tuition Session Fee"
        base_price = fee_amt
        features = [
            f"Tutor: {eng.tutor.display_name}",
            f"Student: {eng.student.name if eng.student else 'Enrolled Student'}",
            f"Schedule: {eng.schedule_summary}",
            "Protected escrow-like settlement with automated receipt generation",
        ]
        metadata['engagement_id'] = eng.id

    else:
        messages.error(request, "Unknown checkout category requested.")
        return redirect('core:pricing')

    item_key = f"{checkout_type}:{metadata.get('plan_id') or metadata.get('credits_count') or metadata.get('commission_id') or metadata.get('invoice_number') or metadata.get('engagement_id')}"

    # Stable session management: preserve order_ref, coupon, and expiration across page refreshes
    checkout_sessions = request.session.get('checkout_sessions', {})
    now_ts = int(timezone.now().timestamp())
    session_data = checkout_sessions.get(item_key)

    if session_data and session_data.get('expires_at', 0) > now_ts:
        order_ref = session_data['order_ref']
        expires_at = session_data['expires_at']
        if not coupon_code and session_data.get('coupon_code'):
            coupon_code = session_data['coupon_code']
    else:
        order_ref = f"ORD-{uuid.uuid4().hex[:7].upper()}"
        expires_at = now_ts + (15 * 60)  # 15-minute stable payment session
        checkout_sessions[item_key] = {
            'order_ref': order_ref,
            'expires_at': expires_at,
            'coupon_code': coupon_code,
        }
        request.session['checkout_sessions'] = checkout_sessions
        request.session.modified = True

    remaining_seconds = max(expires_at - now_ts, 15)

    # Calculate discount & taxes
    discount_amount, coupon_desc, coupon_err = calculate_discount(coupon_code, base_price)
    if coupon_err and coupon_code:
        messages.warning(request, coupon_err)
        coupon_code = ""
        if item_key in checkout_sessions:
            checkout_sessions[item_key]['coupon_code'] = ""
            request.session['checkout_sessions'] = checkout_sessions
            request.session.modified = True
    elif coupon_code and not coupon_err:
        checkout_sessions[item_key]['coupon_code'] = coupon_code
        request.session['checkout_sessions'] = checkout_sessions
        request.session.modified = True

    discounted_subtotal = max(base_price - discount_amount, Decimal('0.00'))
    
    # If commission has its precomputed tax and no coupon, use precomputed; else recalculate
    if checkout_type == 'commission' and commission_obj and discount_amount == Decimal('0.00'):
        tax_amount = commission_obj.tax_amount
        total_payable = commission_obj.total_amount
    else:
        tax_rate = company.tax_percentage if company.tax_percentage else Decimal('18.00')
        tax_amount = round((discounted_subtotal * tax_rate) / Decimal('100.00'), 2)
        total_payable = round(discounted_subtotal + tax_amount, 2)

    cgst_amount = round(tax_amount / Decimal('2.00'), 2)
    sgst_amount = round(tax_amount - cgst_amount, 2)

    # UPI URI with persistent order_ref
    upi_pa = f"edututorpro@hdfcbank"
    upi_qr_string = f"upi://pay?pa={upi_pa}&pn={company.company_name.replace(' ', '+')}&am={total_payable}&cu=INR&tn={order_ref}"

    # Generate real, scannable QR Code base64 image
    qr_base64 = ""
    try:
        import qrcode
        import io
        import base64

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(upi_qr_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        qr_base64 = ""

    context = {
        'company': company,
        'checkout_type': checkout_type,
        'item_title': item_title,
        'item_subtitle': item_subtitle,
        'item_category_badge': item_category_badge,
        'item_key': item_key,
        'base_price': base_price,
        'discount_amount': discount_amount,
        'discounted_subtotal': discounted_subtotal,
        'tax_amount': tax_amount,
        'cgst_amount': cgst_amount,
        'sgst_amount': sgst_amount,
        'total_payable': total_payable,
        'features': features,
        'metadata': metadata,
        'coupon_code': coupon_code,
        'coupon_desc': coupon_desc,
        'available_coupons': PROMO_COUPONS.values(),
        'order_ref': order_ref,
        'remaining_seconds': remaining_seconds,
        'upi_pa': upi_pa,
        'upi_qr_string': upi_qr_string,
        'qr_base64': qr_base64,
        'plan_obj': plan_obj,
        'commission_obj': commission_obj,
        'invoice_obj': invoice_obj,
    }
    return render(request, 'billing/checkout.html', context)


@login_required
def apply_coupon_api(request):
    """AJAX endpoint for instant dynamic coupon code calculation."""
    if request.method != 'POST':
        return HttpResponseBadRequest("POST required")

    try:
        data = json.loads(request.body)
        coupon_code = data.get('coupon_code', '').strip().upper()
        base_amount = Decimal(str(data.get('base_amount', '0')))
        item_key = data.get('item_key', '')
    except Exception:
        coupon_code = request.POST.get('coupon_code', '').strip().upper()
        base_amount = Decimal(str(request.POST.get('base_amount', '0')))
        item_key = request.POST.get('item_key', '')

    company = CompanySettings.get_settings()
    tax_rate = company.tax_percentage if company.tax_percentage else Decimal('18.00')

    # Allow clearing coupon
    if not coupon_code:
        checkout_sessions = request.session.get('checkout_sessions', {})
        if item_key and item_key in checkout_sessions:
            checkout_sessions[item_key]['coupon_code'] = ""
            order_ref = checkout_sessions[item_key]['order_ref']
            request.session['checkout_sessions'] = checkout_sessions
            request.session.modified = True
        else:
            order_ref = f"ORD-{uuid.uuid4().hex[:7].upper()}"

        tax_amount = round((base_amount * tax_rate) / Decimal('100.00'), 2)
        total_payable = round(base_amount + tax_amount, 2)
        upi_pa = f"edututorpro@hdfcbank"
        new_upi_qr_string = f"upi://pay?pa={upi_pa}&pn={company.company_name.replace(' ', '+')}&am={total_payable}&cu=INR&tn={order_ref}"
        new_qr_base64 = ""
        try:
            import qrcode, io, base64
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(new_upi_qr_string)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            new_qr_base64 = base64.b64encode(buf.getvalue()).decode()
        except Exception:
            new_qr_base64 = ""

        return JsonResponse({
            'valid': True,
            'cleared': True,
            'coupon_code': '',
            'discount_amount': 0.0,
            'discount_description': '',
            'tax_amount': float(tax_amount),
            'total_payable': float(total_payable),
            'upi_qr_string': new_upi_qr_string,
            'qr_base64': new_qr_base64,
            'message': 'Coupon removed.'
        })

    discount, desc, err = calculate_discount(coupon_code, base_amount)
    if err:
        return JsonResponse({'valid': False, 'message': err})

    discounted_subtotal = max(base_amount - discount, Decimal('0.00'))
    tax_amount = round((discounted_subtotal * tax_rate) / Decimal('100.00'), 2)
    total_payable = round(discounted_subtotal + tax_amount, 2)

    # Preserve stable order_ref from active checkout session
    checkout_sessions = request.session.get('checkout_sessions', {})
    if item_key and item_key in checkout_sessions:
        order_ref = checkout_sessions[item_key]['order_ref']
        checkout_sessions[item_key]['coupon_code'] = coupon_code
        request.session['checkout_sessions'] = checkout_sessions
        request.session.modified = True
    else:
        order_ref = f"ORD-{uuid.uuid4().hex[:7].upper()}"

    upi_pa = f"edututorpro@hdfcbank"
    new_upi_qr_string = f"upi://pay?pa={upi_pa}&pn={company.company_name.replace(' ', '+')}&am={total_payable}&cu=INR&tn={order_ref}"
    new_qr_base64 = ""
    try:
        import qrcode
        import io
        import base64

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(new_upi_qr_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        new_qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    except Exception:
        new_qr_base64 = ""

    return JsonResponse({
        'valid': True,
        'coupon_code': coupon_code,
        'discount_amount': float(discount),
        'discount_description': desc,
        'tax_amount': float(tax_amount),
        'total_payable': float(total_payable),
        'upi_qr_string': new_upi_qr_string,
        'qr_base64': new_qr_base64,
        'order_ref': order_ref,
        'message': f"Coupon '{coupon_code}' applied successfully! Saved ₹{discount}"
    })


@login_required
def process_payment_view(request):
    """
    Simulated secure payment gateway authorization processor.
    Validates the order, processes the simulated bank transaction,
    creates official Invoice & Payment records, fulfills benefits,
    creates notifications & audit logs, and redirects to Payment Success.
    """
    if request.method != 'POST':
        return redirect('billing:checkout')

    company = CompanySettings.get_settings()
    checkout_type = request.POST.get('checkout_type', 'plan')
    payment_method = request.POST.get('payment_method', Payment.Method.UPI)
    coupon_code = request.POST.get('coupon_code', '').strip().upper()
    simulate_outcome = request.POST.get('simulate_outcome', 'SUCCESS').upper()
    order_ref = request.POST.get('order_ref', '').strip()

    # Idempotency check: if this order was already processed successfully, redirect to existing receipt
    if order_ref:
        existing_payment = Payment.objects.filter(
            user=request.user,
            gateway_reference__startswith=f"{order_ref}:",
            status=Payment.Status.SUCCESSFUL
        ).first()
        if existing_payment:
            messages.info(request, "This payment order has already been completed.")
            return redirect('billing:payment_success', payment_id=existing_payment.payment_id)

    # Read base amounts
    base_price = Decimal(request.POST.get('base_price', '0.00'))
    discount_amount, _, _ = calculate_discount(coupon_code, base_price)
    discounted_subtotal = max(base_price - discount_amount, Decimal('0.00'))
    tax_rate = company.tax_percentage if company.tax_percentage else Decimal('18.00')
    tax_amount = round((discounted_subtotal * tax_rate) / Decimal('100.00'), 2)
    total_payable = round(discounted_subtotal + tax_amount, 2)

    # Allow testing of declined / failed transactions
    if simulate_outcome == 'FAIL':
        failed_ref = f"{order_ref}:DECLINED" if order_ref else f"DECLINED-SIM-{uuid.uuid4().hex[:8].upper()}"
        failed_payment = Payment.objects.create(
            user=request.user,
            amount=total_payable,
            method=payment_method,
            gateway_reference=failed_ref,
            status=Payment.Status.FAILED
        )
        return redirect('billing:payment_failed')

    # Atomic fulfillment
    with transaction.atomic():
        invoice = None
        line_item_description = ""
        success_message = ""

        # 1. Category Fulfillment
        if checkout_type == 'plan':
            plan_id = request.POST.get('plan_id')
            plan = get_object_or_404(SubscriptionPlan, pk=plan_id, is_active=True)
            tprofile = get_object_or_404(TutorProfile, user=request.user)

            # Create or renew subscription
            TutorSubscription.objects.create(
                tutor=tprofile,
                plan=plan,
                start_date=timezone.now().date(),
                end_date=timezone.now().date() + datetime.timedelta(days=plan.duration_days),
                amount_paid=total_payable,
                status=TutorSubscription.Status.ACTIVE
            )

            # Award lead credits to wallet
            wallet = ContactCreditWallet.get_or_create_wallet(tprofile)
            wallet.add_credits(
                amount=plan.lead_credits_included,
                credit_type='PURCHASED',
                reference_note=f"Plan Activation ({plan.name}): +{plan.lead_credits_included} Credits"
            )

            line_item_description = f"Educator Membership: {plan.name} ({plan.duration_days} days validity)"
            success_message = f"Activated {plan.name}! {plan.lead_credits_included} credits added to your wallet."

        elif checkout_type == 'credits':
            credits_count = int(request.POST.get('credits_count', 15))
            tprofile = get_object_or_404(TutorProfile, user=request.user)

            wallet = ContactCreditWallet.get_or_create_wallet(tprofile)
            wallet.add_credits(
                amount=credits_count,
                credit_type='PURCHASED',
                reference_note=f"Recharge Pack: +{credits_count} Verified Contact Unlocks"
            )

            line_item_description = f"Contact Credit Pack: {credits_count} Parent Contact Unlocks"
            success_message = f"Purchased {credits_count} Contact Credits! Added to your wallet."

        elif checkout_type == 'commission':
            comm_id = request.POST.get('commission_id')
            comm = get_object_or_404(CommissionRecord, pk=comm_id)
            comm.status = CommissionRecord.Status.PAID
            comm.paid_at = timezone.now()
            comm.save()

            # Find or link existing invoice if already created during engagement confirmation
            existing_inv = Invoice.objects.filter(
                user=request.user,
                invoice_type=Invoice.InvoiceType.COMMISSION,
                total_amount=comm.total_amount
            ).first()

            if existing_inv:
                invoice = existing_inv
                invoice.status = Invoice.Status.PAID
                invoice.paid_at = timezone.now()
                invoice.save()

            line_item_description = f"Platform Commission [{comm.record_id}] for Engagement {comm.engagement.engagement_id}"
            success_message = f"Commission fee of {company.currency_symbol}{total_payable} settled successfully."

        elif checkout_type == 'invoice':
            inv_num = request.POST.get('invoice_number')
            invoice = get_object_or_404(Invoice, invoice_number=inv_num)
            invoice.status = Invoice.Status.PAID
            invoice.paid_at = timezone.now()
            invoice.save()
            line_item_description = f"Payment for Tax Invoice #{invoice.invoice_number}"
            success_message = f"Invoice #{invoice.invoice_number} paid successfully."

        elif checkout_type == 'tuition_fee':
            eng_id = request.POST.get('engagement_id')
            eng = get_object_or_404(TuitionEngagement, pk=eng_id)
            line_item_description = f"Tuition Session Fee Settlement [{eng.engagement_id}] - {eng.agreed_subjects}"
            success_message = f"Tuition payment of {company.currency_symbol}{total_payable} confirmed."

        # 2. Generate Invoice if not already created
        if not invoice:
            inv_type_map = {
                'plan': Invoice.InvoiceType.SUBSCRIPTION,
                'credits': Invoice.InvoiceType.CREDIT_PURCHASE,
                'commission': Invoice.InvoiceType.COMMISSION,
                'tuition_fee': Invoice.InvoiceType.TUITION_FEE,
                'invoice': Invoice.InvoiceType.CREDIT_PURCHASE
            }
            invoice = Invoice.objects.create(
                user=request.user,
                invoice_type=inv_type_map.get(checkout_type, Invoice.InvoiceType.CREDIT_PURCHASE),
                subtotal=discounted_subtotal,
                tax_amount=tax_amount,
                total_amount=total_payable,
                status=Invoice.Status.PAID,
                paid_at=timezone.now()
            )
            InvoiceLineItem.objects.create(
                invoice=invoice,
                description=line_item_description,
                quantity=1,
                unit_price=discounted_subtotal,
                total_price=discounted_subtotal
            )
            if tax_amount > Decimal('0.00'):
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    description=f"{company.tax_name} ({company.tax_percentage}%)",
                    quantity=1,
                    unit_price=tax_amount,
                    total_price=tax_amount
                )

        # 3. Create Verified Payment record
        gateway_ref = f"{order_ref}:{payment_method}" if order_ref else f"SIM-{payment_method}-{uuid.uuid4().hex[:8].upper()}"
        payment = Payment.objects.create(
            invoice=invoice,
            user=request.user,
            amount=total_payable,
            method=payment_method,
            gateway_reference=gateway_ref,
            status=Payment.Status.SUCCESSFUL
        )

        # 4. Trigger Official Payment Success Email Receipt
        try:
            invoice_url = request.build_absolute_uri(f"/billing/invoice/{invoice.invoice_number}/")
            send_transactional_email(
                subject=f"Payment Receipt: {company.currency_symbol}{total_payable} (Ref: {payment.payment_id})",
                template_name="emails/payment_receipt_email.html",
                context={
                    'user': request.user,
                    'payment': payment,
                    'invoice': invoice,
                    'amount_paid': total_payable,
                    'payment_id': payment.payment_id,
                    'invoice_number': invoice.invoice_number,
                    'invoice_url': invoice_url,
                    'line_item_description': line_item_description,
                    'payment_method': payment.get_method_display() if hasattr(payment, 'get_method_display') else payment_method,
                    'created_at': payment.created_at,
                },
                recipient_list=[request.user.email]
            )
        except Exception:
            pass

        # 5. Create in-app Notification
        try:
            Notification.objects.create(
                user=request.user,
                title="Payment Successful & Verified",
                message=f"Your payment of {company.currency_symbol}{total_payable} for '{line_item_description}' was successful. Ref: {payment.payment_id}.",
                notification_type=Notification.Type.WALLET_ALERT if checkout_type in ['plan', 'credits'] else Notification.Type.COMMISSION_ALERT,
                action_url=reverse('billing:invoice_detail', kwargs={'invoice_number': invoice.invoice_number})
            )
        except Exception:
            pass

        # 5. Log Audit Trail
        try:
            AuditLog.objects.create(
                user=request.user,
                action='PAYMENT_PROCESSED',
                resource_type='Payment',
                resource_id=payment.payment_id,
                details=f"Category: {checkout_type}, Amount: {company.currency_symbol}{total_payable}, Method: {payment_method}, Ref: {gateway_ref}"
            )
        except Exception:
            pass

        # 6. Clear checkout session for this item
        checkout_sessions = request.session.get('checkout_sessions', {})
        item_key = f"{checkout_type}:{request.POST.get('plan_id') or request.POST.get('credits_count') or request.POST.get('commission_id') or request.POST.get('invoice_number') or request.POST.get('engagement_id')}"
        if item_key in checkout_sessions:
            del checkout_sessions[item_key]
            request.session['checkout_sessions'] = checkout_sessions
            request.session.modified = True

    messages.success(request, success_message)
    return redirect('billing:payment_success', payment_id=payment.payment_id)


@login_required
def payment_success_view(request, payment_id):
    """Modern, celebratory Payment Receipt & Confirmation View."""
    payment = get_object_or_404(Payment, payment_id=payment_id)
    if payment.user != request.user and not (request.user.is_super_admin or request.user.is_operations):
        messages.error(request, "Unauthorized to view this payment confirmation.")
        return redirect('core:home')

    company = CompanySettings.get_settings()
    wallet = None
    if hasattr(request.user, 'tutor_profile'):
        wallet = ContactCreditWallet.get_or_create_wallet(request.user.tutor_profile)

    context = {
        'company': company,
        'payment': payment,
        'invoice': payment.invoice,
        'wallet': wallet,
    }
    return render(request, 'billing/payment_success.html', context)


@login_required
def payment_failed_view(request):
    """User-friendly payment declined / failed state."""
    company = CompanySettings.get_settings()
    return render(request, 'billing/payment_failed.html', {'company': company})


@login_required
def purchase_subscription_view(request, plan_id):
    """
    Backwards-compatible endpoint for subscription plan purchase.
    GET requests route directly to the checkout page.
    POST requests maintain programmatic test compatibility.
    """
    if request.method == 'GET':
        return redirect(f"{reverse('billing:checkout')}?type=plan&id={plan_id}")

    if not request.user.is_tutor and not request.user.is_super_admin:
        messages.error(request, "Only tutors can purchase educator membership plans.")
        return redirect('accounts:dashboard_redirect')

    tprofile = get_object_or_404(TutorProfile, user=request.user)
    plan = get_object_or_404(SubscriptionPlan, pk=plan_id, is_active=True)
    company = CompanySettings.get_settings()

    # Create active subscription
    sub = TutorSubscription.objects.create(
        tutor=tprofile,
        plan=plan,
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + datetime.timedelta(days=plan.duration_days),
        amount_paid=plan.price,
        status=TutorSubscription.Status.ACTIVE
    )

    # Award lead credits to wallet
    wallet = ContactCreditWallet.get_or_create_wallet(tprofile)
    wallet.add_credits(
        amount=plan.lead_credits_included,
        credit_type='PURCHASED',
        reference_note=f"Membership Plan Benefit ({plan.name}): +{plan.lead_credits_included} Credits"
    )

    # Generate Invoice
    tax_amt = (plan.price * company.tax_percentage) / Decimal('100.00')
    total_amt = plan.price + tax_amt
    inv = Invoice.objects.create(
        user=request.user,
        invoice_type=Invoice.InvoiceType.SUBSCRIPTION,
        subtotal=plan.price,
        tax_amount=tax_amt,
        total_amount=total_amt,
        status=Invoice.Status.PAID,
        paid_at=timezone.now()
    )
    InvoiceLineItem.objects.create(
        invoice=inv,
        description=f"Educator Membership: {plan.name} ({plan.duration_days} days)",
        quantity=1,
        unit_price=plan.price,
        total_price=plan.price
    )
    payment = Payment.objects.create(
        invoice=inv,
        user=request.user,
        amount=total_amt,
        method=Payment.Method.UPI,
        gateway_reference=f"UPI-SIM-{inv.invoice_number}",
        status=Payment.Status.SUCCESSFUL
    )

    messages.success(request, f"Successfully subscribed to {plan.name}! {plan.lead_credits_included} credits added to your wallet.")
    return redirect('billing:payment_success', payment_id=payment.payment_id)


@login_required
def purchase_credit_pack_view(request):
    """
    Backwards-compatible endpoint for credit pack purchase.
    GET requests route directly to the checkout page.
    POST requests maintain programmatic test compatibility.
    """
    if request.method == 'GET':
        credits = request.GET.get('credits', 15)
        amount = request.GET.get('amount', 699)
        return redirect(f"{reverse('billing:checkout')}?type=credits&credits={credits}&amount={amount}")

    if not request.user.is_tutor and not request.user.is_super_admin:
        return redirect('accounts:dashboard_redirect')

    tprofile = get_object_or_404(TutorProfile, user=request.user)
    company = CompanySettings.get_settings()

    credits_count = int(request.POST.get('credits', 15))
    amount = Decimal(request.POST.get('amount', 699))

    wallet = ContactCreditWallet.get_or_create_wallet(tprofile)
    wallet.add_credits(
        amount=credits_count,
        credit_type='PURCHASED',
        reference_note=f"Purchased Contact Credit Pack: +{credits_count} Credits"
    )

    tax_amt = (amount * company.tax_percentage) / Decimal('100.00')
    total_amt = amount + tax_amt
    inv = Invoice.objects.create(
        user=request.user,
        invoice_type=Invoice.InvoiceType.CREDIT_PURCHASE,
        subtotal=amount,
        tax_amount=tax_amt,
        total_amount=total_amt,
        status=Invoice.Status.PAID,
        paid_at=timezone.now()
    )
    InvoiceLineItem.objects.create(
        invoice=inv,
        description=f"Contact Credit Pack: {credits_count} Unlocks",
        quantity=1,
        unit_price=amount,
        total_price=amount
    )
    payment = Payment.objects.create(
        invoice=inv,
        user=request.user,
        amount=total_amt,
        method=Payment.Method.UPI,
        gateway_reference=f"UPI-SIM-{inv.invoice_number}",
        status=Payment.Status.SUCCESSFUL
    )

    messages.success(request, f"Credit pack purchased! {credits_count} credits added to your wallet.")
    return redirect('billing:payment_success', payment_id=payment.payment_id)


@login_required
def invoice_detail_view(request, invoice_number):
    """Tax invoice detail and printable receipt view."""
    invoice = get_object_or_404(Invoice, invoice_number=invoice_number)
    if invoice.user != request.user and not (request.user.is_super_admin or request.user.is_operations):
        messages.error(request, "Unauthorized to view this invoice.")
        return redirect('core:home')

    company = CompanySettings.get_settings()
    return render(request, 'billing/invoice_detail.html', {'invoice': invoice, 'company': company})
