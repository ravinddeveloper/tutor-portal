import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def send_transactional_email(subject, template_name, context, recipient_list, from_email=None):
    """
    Centralized transactional email service for EduTutor Pro.
    Sends both plain-text and HTML versions using Django's EmailMultiAlternatives.
    Catches all exceptions gracefully and logs failures so user workflows are never crashed.

    :param subject: Email subject line string
    :param template_name: Relative path to the HTML template (e.g., 'emails/welcome_email.html')
    :param context: Dictionary containing template context variables
    :param recipient_list: List of email addresses or a single recipient email string
    :param from_email: Optional custom sender address (defaults to settings.DEFAULT_FROM_EMAIL)
    :return: Boolean indicating whether email was dispatched successfully
    """
    if not recipient_list:
        logger.warning(f"send_transactional_email called with empty recipient_list for subject: '{subject}'")
        return False

    if isinstance(recipient_list, str):
        recipient_list = [recipient_list]

    # Clean and filter recipients
    recipient_list = [r.strip() for r in recipient_list if r and isinstance(r, str) and r.strip()]
    if not recipient_list:
        logger.warning(f"No valid recipient email addresses found for subject: '{subject}'")
        return False

    # Inject global company branding if available and not explicitly provided
    if context is None:
        context = {}
    if 'company' not in context:
        try:
            from apps.core.models import CompanySettings
            context['company'] = CompanySettings.get_settings()
        except Exception:
            pass

    sender = from_email or settings.DEFAULT_FROM_EMAIL

    try:
        # Render HTML version from template
        html_content = render_to_string(template_name, context)

        # Generate readable plain-text fallback
        text_content = strip_tags(html_content)

        # Build multipart message
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=sender,
            to=recipient_list
        )
        msg.attach_alternative(html_content, "text/html")

        # Dispatch message
        msg.send(fail_silently=False)
        logger.info(f"Transactional email '{subject}' sent successfully to {recipient_list}")
        return True

    except Exception as exc:
        logger.error(
            f"Failed to send transactional email '{subject}' to {recipient_list}: {exc}",
            exc_info=True
        )
        return False
