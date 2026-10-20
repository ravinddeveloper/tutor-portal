from django.contrib import admin
from apps.core.models import CompanySettings, ThemeSettings, Announcement, AuditLog, ContactEnquiry

@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'support_email', 'support_phone', 'commission_enabled', 'updated_at')

@admin.register(ThemeSettings)
class ThemeSettingsAdmin(admin.ModelAdmin):
    list_display = ('theme_preset', 'primary_color', 'secondary_color', 'dark_mode_enabled', 'updated_at')

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'badge_text', 'target_role', 'priority', 'is_published', 'created_at')
    list_filter = ('target_role', 'priority', 'is_published')
    search_fields = ('title', 'content')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'resource_type', 'resource_id', 'ip_address')
    list_filter = ('action', 'resource_type')
    search_fields = ('action', 'resource_type', 'resource_id', 'details')

@admin.register(ContactEnquiry)
class ContactEnquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'subject', 'source_page', 'status', 'created_at')
    list_filter = ('status', 'source_page', 'created_at')
    search_fields = ('name', 'email', 'phone', 'subject', 'message', 'admin_notes')
    readonly_fields = ('created_at', 'updated_at')
