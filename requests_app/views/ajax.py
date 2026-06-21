# requests_app/views/ajax.py
import json
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from buildings.models import Building
from ..models import ServiceRequest
from users.models import User


@login_required
def api_building_sections(request):
    building_id = request.GET.get('building_id')
    if not building_id:
        return JsonResponse([], safe=False)
    try:
        building = Building.objects.get(pk=building_id)
        sections = building.sections.all().values('id', 'name')
        return JsonResponse(list(sections), safe=False)
    except Building.DoesNotExist:
        return JsonResponse([], safe=False)


@login_required
def api_overdue_requests(request):
    from datetime import date
    assignee_id = request.GET.get('assignee_id')
    if not assignee_id or not assignee_id.isdigit():
        return JsonResponse({'error': 'Не указан ID исполнителя'}, status=400)
    try:
        user_obj = User.objects.get(pk=int(assignee_id))
    except User.DoesNotExist:
        return JsonResponse({'error': 'Исполнитель не найден'}, status=404)
    today = date.today()
    overdue_requests = ServiceRequest.objects.filter(
        planned_date__lt=today,
        status__in=['new', 'in_progress', 'suspended']
    ).filter(Q(assigned_to=user_obj) | Q(assignees__user=user_obj)).distinct()
    requests_data = []
    for req in overdue_requests:
        requests_data.append({
            'id': req.id,
            'request_number': req.request_number,
            'description': req.description,
            'planned_date': req.planned_date.strftime('%d.%m.%Y') if req.planned_date else '',
            'status_display': req.get_status_display(),
        })
    return JsonResponse({'requests': requests_data})