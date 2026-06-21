# assets/views.py
# Полная версия с поддержкой инвентаризации через камеру, AJAX, офлайн-синхронизацией и API

import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from django.utils import timezone

# REST Framework для API
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import UserRole
from .models import Asset, AssetCategory, AssetAssignment, AssetCheck
from .forms import AssetForm, AssetAssignmentForm, AssetCheckForm
from .serializers import AssetSimpleSerializer, InventorySyncSerializer

logger = logging.getLogger(__name__)


# ---------- PERMISSION HELPERS ----------
def can_edit_asset(user, asset=None):
    if user.is_superuser:
        return True
    role = getattr(user, 'profile', None)
    if role and role.role in [UserRole.ADMIN, UserRole.ENGINEER]:
        return True
    return False

def can_delete_asset(user):
    if user.is_superuser:
        return True
    role = getattr(user, 'profile', None)
    return role and role.role == UserRole.ADMIN

def can_assign_asset(user):
    if user.is_superuser:
        return True
    role = getattr(user, 'profile', None)
    return role and role.role in [UserRole.ADMIN, UserRole.ENGINEER]


# ---------- CRUD (CBV) ----------
class AssetListView(LoginRequiredMixin, ListView):
    model = Asset
    template_name = 'assets/asset_list.html'
    context_object_name = 'assets'
    paginate_by = 20

    def get_queryset(self):
        qs = Asset.objects.select_related('category', 'responsible_person').all()
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(inventory_number__icontains=search) |
                Q(name__icontains=search) |
                Q(serial_number__icontains=search) |
                Q(location__icontains=search)
            )
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        category_id = self.request.GET.get('category_id')
        if category_id and category_id != 'all':
            qs = qs.filter(category_id=category_id)
        responsible = self.request.GET.get('responsible')
        if responsible:
            qs = qs.filter(responsible_person_id=responsible)
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = AssetCategory.objects.annotate(
            asset_count=Count('assets')
        ).order_by('name')
        context['categories'] = categories
        context['selected_category_id'] = self.request.GET.get('category_id', 'all')
        base_query = self.request.GET.copy()
        base_query.pop('category_id', None)
        context['base_query'] = base_query.urlencode()
        context['total_assets'] = Asset.objects.count()
        context['status_choices'] = Asset.STATUS_CHOICES
        context['users'] = User.objects.filter(is_active=True).order_by('username')
        context['selected_status'] = self.request.GET.get('status')
        context['selected_responsible'] = self.request.GET.get('responsible')
        context['search'] = self.request.GET.get('search')
        context['can_edit'] = can_edit_asset(self.request.user)
        context['can_delete'] = can_delete_asset(self.request.user)
        context['can_assign'] = can_assign_asset(self.request.user)
        return context


class AssetDetailView(LoginRequiredMixin, DetailView):
    model = Asset
    template_name = 'assets/asset_detail.html'
    context_object_name = 'asset'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset = self.get_object()
        context['assignments'] = asset.assignments.all().order_by('-assigned_at')
        context['checks'] = asset.checks.all().order_by('-checked_at')
        context['can_edit'] = can_edit_asset(self.request.user, asset)
        context['can_delete'] = can_delete_asset(self.request.user)
        context['can_assign'] = can_assign_asset(self.request.user)
        return context


class AssetCreateView(LoginRequiredMixin, CreateView):
    model = Asset
    form_class = AssetForm
    template_name = 'assets/asset_form.html'
    success_url = reverse_lazy('assets:asset_list')

    def dispatch(self, request, *args, **kwargs):
        if not can_edit_asset(request.user):
            messages.error(request, 'У вас нет прав на создание имущества.')
            return redirect('assets:asset_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, 'Имущество успешно создано.')
        return super().form_valid(form)


class AssetUpdateView(LoginRequiredMixin, UpdateView):
    model = Asset
    form_class = AssetForm
    template_name = 'assets/asset_form.html'
    success_url = reverse_lazy('assets:asset_list')

    def dispatch(self, request, *args, **kwargs):
        if not can_edit_asset(request.user, self.get_object()):
            messages.error(request, 'У вас нет прав на редактирование этого имущества.')
            return redirect('assets:asset_detail', pk=self.get_object().pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, 'Имущество успешно обновлено.')
        return super().form_valid(form)


class AssetDeleteView(LoginRequiredMixin, DeleteView):
    model = Asset
    template_name = 'assets/asset_confirm_delete.html'
    success_url = reverse_lazy('assets:asset_list')

    def dispatch(self, request, *args, **kwargs):
        if not can_delete_asset(request.user):
            messages.error(request, 'У вас нет прав на удаление имущества.')
            return redirect('assets:asset_list')
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Имущество успешно удалено.')
        return super().delete(request, *args, **kwargs)


# ---------- ДЕЙСТВИЯ (FBV) ----------
@login_required
def assign_asset(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    if not can_assign_asset(request.user):
        messages.error(request, 'У вас нет прав на закрепление имущества.')
        return redirect('assets:asset_detail', pk=asset.pk)

    if request.method == 'POST':
        form = AssetAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.asset = asset
            asset.responsible_person = assignment.assigned_to
            asset.save()
            assignment.save()
            messages.success(request, f'Имущество закреплено за {assignment.assigned_to}.')
            return redirect('assets:asset_detail', pk=asset.pk)
    else:
        form = AssetAssignmentForm(initial={'assigned_to': asset.responsible_person})
    return render(request, 'assets/assign_asset.html', {'form': form, 'asset': asset})


@login_required
def return_asset(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    if not can_assign_asset(request.user):
        messages.error(request, 'У вас нет прав на возврат имущества.')
        return redirect('assets:asset_detail', pk=asset.pk)

    if request.method == 'POST':
        assignment = asset.assignments.filter(returned_at__isnull=True).first()
        if assignment:
            assignment.returned_at = timezone.now()
            assignment.save()
        asset.responsible_person = None
        asset.save()
        messages.success(request, 'Имущество возвращено на склад.')
        return redirect('assets:asset_detail', pk=asset.pk)
    return render(request, 'assets/return_asset.html', {'asset': asset})


@login_required
def add_asset_check(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    if not can_edit_asset(request.user, asset):
        messages.error(request, 'У вас нет прав на проведение проверки.')
        return redirect('assets:asset_detail', pk=asset.pk)

    if request.method == 'POST':
        form = AssetCheckForm(request.POST)
        if form.is_valid():
            check = form.save(commit=False)
            check.asset = asset
            check.checked_by = request.user
            check.save()
            messages.success(request, 'Проверка сохранена.')
            return redirect('assets:asset_detail', pk=asset.pk)
    else:
        form = AssetCheckForm()
    return render(request, 'assets/add_check.html', {'form': form, 'asset': asset})


@login_required
def generate_asset_qr(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    if not asset.qr_code:
        asset.generate_qr_code()
        asset.save()
    return redirect('assets:asset_detail', pk=asset.pk)


@login_required
def download_asset_qr(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    if not asset.qr_code:
        messages.error(request, 'QR-код не сгенерирован.')
        return redirect('assets:asset_detail', pk=asset.pk)
    response = HttpResponse(asset.qr_code, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="{asset.inventory_number}.png"'
    return response


@login_required
def asset_report(request):
    if not can_edit_asset(request.user):
        messages.error(request, 'У вас нет доступа к отчётам.')
        return redirect('assets:asset_list')
    qs = Asset.objects.select_related('category', 'responsible_person').all()
    context = {
        'assets': qs,
        'total': qs.count(),
        'by_status': {s: qs.filter(status=s).count() for s, _ in Asset.STATUS_CHOICES},
    }
    return render(request, 'assets/asset_report.html', context)


# ---------- ИНВЕНТАРИЗАЦИЯ ----------
@login_required
def inventory_asset(request, pk):
    """Отметка имущества в инвентаризации (вызывается по QR-ссылке)."""
    asset = get_object_or_404(Asset, pk=pk)
    today = timezone.now().date()
    existing = AssetCheck.objects.filter(
        asset=asset,
        checked_by=request.user,
        checked_at__date=today
    ).first()
    if existing:
        messages.info(request, f'Имущество "{asset.name}" уже было отмечено сегодня.')
    else:
        check = AssetCheck(
            asset=asset,
            checked_by=request.user,
            condition='good',
            notes=f"Отмечено при инвентаризации {timezone.now().strftime('%d.%m.%Y %H:%M')}"
        )
        check.save()
        messages.success(request, f'Имущество "{asset.name}" отмечено в инвентаризации.')
    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('assets:asset_detail', pk=asset.pk)


@login_required
def inventory_scan(request):
    """Страница инвентаризации с камерой и списком отсканированных объектов."""
    today = timezone.now().date()
    scans_today = AssetCheck.objects.filter(
        checked_by=request.user,
        checked_at__date=today
    ).select_related('asset').order_by('-checked_at')
    return render(request, 'assets/inventory_scan.html', {'scans': scans_today})


@login_required
def inventory_scan_ajax(request):
    """
    AJAX-обработчик сканирования QR-кода.
    Принимает POST с inventory_number, создаёт запись проверки и возвращает данные актива.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Метод не разрешён'}, status=405)

    inventory_number = request.POST.get('inventory_number', '').strip()
    if not inventory_number:
        return JsonResponse({'success': False, 'error': 'Не указан инвентарный номер'})

    asset = Asset.objects.filter(inventory_number=inventory_number).first()
    if not asset:
        return JsonResponse({'success': False, 'error': 'Имущество не найдено'})

    today = timezone.now().date()
    existing = AssetCheck.objects.filter(
        asset=asset,
        checked_by=request.user,
        checked_at__date=today
    ).first()
    if existing:
        return JsonResponse({
            'success': False,
            'error': 'Уже отмечено сегодня',
            'asset': {
                'id': asset.id,
                'name': asset.name,
                'inventory_number': asset.inventory_number,
                'already_scanned': True
            }
        })

    check = AssetCheck(
        asset=asset,
        checked_by=request.user,
        condition='good',
        notes=f"Отмечено при инвентаризации {timezone.now().strftime('%d.%m.%Y %H:%M')}"
    )
    check.save()

    return JsonResponse({
        'success': True,
        'asset': {
            'id': asset.id,
            'name': asset.name,
            'inventory_number': asset.inventory_number,
            'scanned_at': check.checked_at.strftime('%d.%m.%Y %H:%M'),
            'checked_by': request.user.get_full_name() or request.user.username,
        }
    })


@login_required
def inventory_history(request):
    """История инвентаризаций (список всех проверок)."""
    checks = AssetCheck.objects.select_related('asset', 'checked_by').order_by('-checked_at')
    paginator = Paginator(checks, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'assets/inventory_history.html', {'page_obj': page_obj})


# ---------- API ДЛЯ ОФЛАЙН-ИНВЕНТАРИЗАЦИИ ----------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def asset_list_api(request):
    """
    Возвращает список всех активов (id, инвентарный номер, название).
    Используется для кэширования на клиенте при офлайн-работе.
    """
    assets = Asset.objects.all().only('id', 'inventory_number', 'name')
    serializer = AssetSimpleSerializer(assets, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def inventory_sync_api(request):
    """
    Принимает список инвентарных номеров и создаёт записи AssetCheck для текущего пользователя.
    Используется для синхронизации офлайн-отметок после восстановления соединения.
    """
    serializer = InventorySyncSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    inventory_numbers = serializer.validated_data['inventory_numbers']
    user = request.user
    created_count = 0
    errors = []

    for inv_number in inventory_numbers:
        try:
            asset = Asset.objects.get(inventory_number=inv_number)
        except Asset.DoesNotExist:
            errors.append(f'Не найден актив с номером {inv_number}')
            continue

        today = timezone.now().date()
        if AssetCheck.objects.filter(asset=asset, checked_by=user, checked_at__date=today).exists():
            continue  # пропускаем дубли

        AssetCheck.objects.create(
            asset=asset,
            checked_by=user,
            condition='good',
            notes=f'Отмечено офлайн {timezone.now().strftime("%d.%m.%Y %H:%M")}'
        )
        created_count += 1

    return Response({
        'success': True,
        'created': created_count,
        'errors': errors
    })