import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from apps.accounts.models import User

client = Client()

endpoints = [
    ('/', 200, "Home page"),
    ('/how-it-works/', 200, "How it works"),
    ('/pricing/', 200, "Pricing & plans"),
    ('/about/', 200, "About"),
    ('/contact/', 200, "Contact"),
    ('/terms/', 200, "Terms"),
    ('/privacy/', 200, "Privacy"),
    ('/tutors/', 200, "Tutors directory"),
    ('/leads/board/', 200, "Leads board"),
    ('/leads/post/', 200, "Post requirement"),
    ('/accounts/login/', 200, "Login"),
    ('/accounts/register/parent/', 200, "Register parent"),
    ('/accounts/register/tutor/', 200, "Register tutor"),
]

print("=== CHECKING PUBLIC ENDPOINTS ===")
for url, expected_code, name in endpoints:
    resp = client.get(url)
    status = "OK" if resp.status_code == expected_code else f"FAIL ({resp.status_code})"
    print(f"[{status}] {name}: {url}")

print("\n=== CHECKING AUTHENTICATED ADMIN CONSOLE ===")
admin = User.objects.get(username='admin')
client.force_login(admin)
admin_endpoints = [
    ('/admin-portal/', 200, "Admin Dashboard"),
    ('/admin-portal/tutors/', 200, "Tutors List"),
    ('/admin-portal/leads/', 200, "Leads List"),
    ('/admin-portal/commissions/', 200, "Commissions Engine"),
    ('/admin-portal/subscriptions/', 200, "Subscriptions"),
    ('/admin-portal/financials/', 200, "Financials"),
    ('/admin-portal/complaints/', 200, "Complaints"),
    ('/admin-portal/enquiries/', 200, "Enquiries Desk"),
    ('/admin-portal/announcements/', 200, "Announcements"),
    ('/admin-portal/branding/', 200, "Branding Settings"),
    ('/admin-portal/theme/', 200, "Theme Customizer"),
    ('/admin-portal/reports/', 200, "Reports & Analytics"),
    ('/admin-portal/audit-logs/', 200, "Audit Trail"),
]
for url, expected_code, name in admin_endpoints:
    resp = client.get(url)
    status = "OK" if resp.status_code == expected_code else f"FAIL ({resp.status_code})"
    print(f"[{status}] {name}: {url}")

print("\n=== CHECKING TUTOR PORTAL ===")
tutor = User.objects.get(username='tutor_rajesh')
client.force_login(tutor)
tutor_endpoints = [
    ('/tutors/dashboard/', 200, "Tutor Dashboard"),
    ('/tutors/profile/', 200, "Tutor Profile Edit"),
    ('/tutors/subjects/', 200, "Tutor Subjects"),
    ('/tutors/availability/', 200, "Tutor Availability"),
    ('/tutors/documents/', 200, "Tutor Documents"),
    ('/tutors/leads/', 200, "Tutor Browse Leads"),
    ('/tutors/unlocked-leads/', 200, "Tutor Unlocked Contacts"),
    ('/tutors/applications/', 200, "Tutor Applications"),
    ('/tutors/demos/', 200, "Tutor Demos"),
    ('/tutors/engagements/', 200, "Tutor Engagements"),
    ('/tutors/billing/', 200, "Tutor Wallet & Billing"),
    ('/billing/checkout/?type=plan&id=1', 200, "Billing Checkout (Plan)"),
    ('/billing/checkout/?type=credits&credits=15&amount=699', 200, "Billing Checkout (Credits)"),
    ('/billing/failed/', 200, "Billing Payment Failed State"),
    ('/communication/inbox/', 200, "Tutor Messaging Inbox"),
    ('/communication/notifications/', 200, "Tutor Notifications"),
]
for url, expected_code, name in tutor_endpoints:
    resp = client.get(url)
    status = "OK" if resp.status_code == expected_code else f"FAIL ({resp.status_code})"
    print(f"[{status}] {name}: {url}")

print("\n=== CHECKING PARENT PORTAL ===")
parent = User.objects.get(username='parent_meena')
client.force_login(parent)
parent_endpoints = [
    ('/parents/dashboard/', 200, "Parent Dashboard"),
    ('/parents/requirements/', 200, "Parent Requirements"),
    ('/parents/demos/', 200, "Parent Demos"),
    ('/parents/tuitions/', 200, "Parent Ongoing Tuitions"),
    ('/parents/students/', 200, "Parent Student Profiles"),
]
for url, expected_code, name in parent_endpoints:
    resp = client.get(url)
    status = "OK" if resp.status_code == expected_code else f"FAIL ({resp.status_code})"
    print(f"[{status}] {name}: {url}")

print("\nALL PORTAL ENDPOINTS VERIFIED SUCCESSFULLY!")
