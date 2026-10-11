from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from apps.communication.models import Conversation, Message, Notification
from apps.accounts.models import User

@login_required
def inbox_view(request):
    """Inbox showing active conversations."""
    conversations = Conversation.objects.filter(
        Q(user_a=request.user) | Q(user_b=request.user)
    ).order_by('-updated_at')

    # Start new chat action
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient_id')
        body = request.POST.get('body', '').strip()
        recipient = get_object_or_404(User, pk=recipient_id)

        chat = Conversation.objects.filter(
            (Q(user_a=request.user) & Q(user_b=recipient)) |
            (Q(user_a=recipient) & Q(user_b=request.user))
        ).first()

        if not chat:
            chat = Conversation.objects.create(user_a=request.user, user_b=recipient)

        if body:
            Message.objects.create(conversation=chat, sender=request.user, body=body)
            chat.save() # update timestamp

        return redirect('communication:detail', conversation_id=chat.id)

    return render(request, 'communication/inbox.html', {'conversations': conversations})

@login_required
def conversation_detail_view(request, conversation_id):
    chat = get_object_or_404(
        Conversation.objects.filter(Q(user_a=request.user) | Q(user_b=request.user)),
        pk=conversation_id
    )

    other_user = chat.get_other_participant(request.user)

    # Mark unread messages sent by other user as read
    chat.messages.filter(sender=other_user, is_read=False).update(is_read=True)

    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        if body:
            Message.objects.create(conversation=chat, sender=request.user, body=body)
            chat.save()
            return redirect('communication:detail', conversation_id=chat.id)

    messages_list = chat.messages.all().order_by('created_at')

    return render(request, 'communication/conversation_detail.html', {
        'chat': chat,
        'other_user': other_user,
        'messages_list': messages_list,
    })

@login_required
def notifications_list_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    if request.method == 'POST' and request.POST.get('action') == 'mark_all_read':
        notifications.update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect('communication:notifications')

    return render(request, 'communication/notifications.html', {'notifications': notifications})
