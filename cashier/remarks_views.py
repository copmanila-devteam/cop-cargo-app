import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import Cashier, RemarksList

# UserType.type codes allowed to leave a remark: Pastor, Finance (cashier), Accountant
REMARK_ROLES = ('PTR', 'FI', 'ACNT')


def serialize_remark(remark):
    user = remark.user
    return {
        'description': remark.description,
        'timestamp': timezone.localtime(remark.timestamp).isoformat(),
        'user_name': f'{user.first_name or ""} {user.last_name or ""}'.strip() or user.email,
    }


def get_role_remarks(cashier):
    # """Latest remark per role for a Cashier entry: {'PTR': {...} | None, 'FI': ..., 'ACNT': ...}."""
    result = {role: None for role in REMARK_ROLES}
    entries = (RemarksList.objects
               .filter(cashier=cashier, user__isnull=False)
               .select_related('user')
               .order_by('timestamp'))
    for remark in entries:  # ascending, so the latest remark of each role wins
        if remark.user.type in result:
            result[remark.user.type] = serialize_remark(remark)
    return result


@login_required
@require_GET
def get_remarks(request, pk):
    """System remarks plus the latest remark per role for Cashier entry `pk`."""
    if request.user.type not in REMARK_ROLES:
        return JsonResponse({'status': 'error', 'message': 'You are not allowed to view remarks'}, status=403)

    cashier = get_object_or_404(Cashier, pk=pk)
    return JsonResponse({
        'status': 'success',
        'data': {
            'remarks': cashier.remarks,
            'role_remarks': get_role_remarks(cashier),
        },
    })


@login_required
@require_POST
def submit_remark(request, pk):
    """Save the logged-in user's remark for Cashier entry `pk`."""
    if request.user.type not in REMARK_ROLES:
        return JsonResponse({'status': 'error', 'message': 'You are not allowed to add remarks'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    description = (data.get('remarks') or '').strip()
    if not description:
        return JsonResponse({'status': 'error', 'message': 'Remark cannot be empty'}, status=400)
    if len(description) > 300:
        return JsonResponse({'status': 'error', 'message': 'Remark must be 300 characters or fewer'}, status=400)

    cashier = get_object_or_404(Cashier, pk=pk)

    # One remark per user per entry. Resubmitting edits it; the timestamp is
    # refreshed manually because the field is auto_now_add.
    remark, _ = RemarksList.objects.update_or_create(
        cashier=cashier, user=request.user,
        defaults={'description': description, 'timestamp': timezone.now()},
    )

    return JsonResponse({
        'status': 'success',
        'message': 'Remark saved',
        'role': request.user.type,
        'remark': serialize_remark(remark),
    })
