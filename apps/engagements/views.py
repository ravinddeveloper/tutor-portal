from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.engagements.models import Review, Complaint
from apps.leads.models import TuitionRequirement

def reviews_view(request):
    reviews = Review.objects.filter(is_approved=True).select_related('tutor__user', 'parent__user')
    return render(request, 'engagements/reviews.html', {'reviews': reviews})

@login_required
def file_complaint_view(request):
    if request.method == 'POST':
        category = request.POST.get('category', Complaint.Category.OTHER)
        subject = request.POST.get('subject', '').strip()
        description = request.POST.get('description', '').strip()
        lead_id = request.POST.get('lead_id')

        req = TuitionRequirement.objects.filter(lead_id=lead_id).first() if lead_id else None

        comp = Complaint.objects.create(
            filed_by=request.user,
            requirement=req,
            category=category,
            subject=subject,
            description=description,
            status=Complaint.Status.OPEN
        )
        messages.success(request, f"Your support ticket [{comp.complaint_id}] has been submitted. Platform operations staff will review and contact you.")
        return redirect('core:home')

    return render(request, 'engagements/file_complaint.html')
