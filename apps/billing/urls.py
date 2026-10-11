from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    # Dedicated Checkout & Payment Gateway
    path('checkout/', views.checkout_view, name='checkout'),
    path('checkout/process/', views.process_payment_view, name='process_payment'),
    path('checkout/apply-coupon/', views.apply_coupon_api, name='apply_coupon'),
    path('success/<str:payment_id>/', views.payment_success_view, name='payment_success'),
    path('failed/', views.payment_failed_view, name='payment_failed'),

    # Programmatic & Direct Plan & Pack Endpoints (Preserved for compatibility)
    path('subscribe/<int:plan_id>/', views.purchase_subscription_view, name='purchase_subscription'),
    path('buy-credits/', views.purchase_credit_pack_view, name='purchase_credit_pack'),
    path('invoice/<str:invoice_number>/', views.invoice_detail_view, name='invoice_detail'),
]
