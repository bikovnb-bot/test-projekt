# requests_app/views/requests_cbv.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import Q
from datetime import date
from django.utils import timezone

from users.models import UserRole
from ..models import ServiceRequest, RequestSettings, RequestType
from ..forms import ServiceRequestForm
from .permissions import can_view_request, can_edit_request, can_delete_request
from ..services import RequestService
from buildings.models import Building


class RequestListView(LoginRequiredMixin, ListView):
    model = ServiceRequest
    template_name = 'requests_app/request_list.html'
    context_object_name = 'requests'
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        role = user.profile.role if hasattr(user, 'profile') else None

        qs = ServiceRequest.objects.select_related(
            'building', 'section', 'created_by', 'assigned_to'
        ).only(
            'id', 'request_number', 'building__name', 'building__address',
            'section__name', 'room_number', 'priority', 'status',
            'created_by__username', 'created_by__first_name', 'created_by__last_name',
            'assigned_to__username', 'assigned_to__first_name', 'assigned_to__last_name',
            'created_at', 'description', 'contact_name'
        )

        if role == UserRole.WORKER:
            qs = qs.filter(Q(assigned_to=user) | Q(assignees__user=user)).distinct()
        elif role not in [UserRole.ADMIN, UserRole.ENGINEER, UserRole.DISPATCHER]:
            qs = qs.filter(created_by=user)

        status = self.request.GET.get('status')
        executor = self.request.GET.get('executor')
        priority = self.request.GET.get('priority')
        search = self.request.GET.get('search')
        overdue = self.request.GET.get('overdue')
        building = self.request.GET.get('building')
        request_type = self.request.GET.get('request_type')
        room_number = self.request.GET.get('room_number')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if status:
            qs = qs.filter(status=status)
        if executor:
            qs = qs.filter(assigned_to_id=executor)
        if priority:
            qs = qs.filter(priority=priority)
        if search:
            qs = qs.filter(
                Q(request_number__icontains=search) |
                Q(description__icontains=search) |
                Q(building__address__icontains=search) |
                Q(building__name__icontains=search) |
                Q(contact_name__icontains=search) |
                Q(created_by__first_name__icontains=search) |
                Q(created_by__last_name__icontains=search)
            )
        if overdue:
            qs = qs.filter(
                planned_date__lt=date.today(),
                status__in=['new', 'in_progress', 'suspended']
            )
        if building:
            qs = qs.filter(building_id=building)
        if request_type:
            qs = qs.filter(request_type_id=request_type)
        if room_number:
            qs = qs.filter(room_number__icontains=room_number)
        if date_from:
            from django.utils import dateparse
            parsed = dateparse.parse_date(date_from)
            if parsed:
                qs = qs.filter(created_at__date__gte=parsed)
        if date_to:
            parsed = dateparse.parse_date(date_to)
            if parsed:
                qs = qs.filter(created_at__date__lte=parsed)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        role = user.profile.role if hasattr(user, 'profile') else None

        executors = User.objects.filter(profile__role=UserRole.WORKER).order_by('username')
        status_choices = ServiceRequest.STATUS_CHOICES
        priority_choices = ServiceRequest.PRIORITY_CHOICES
        all_users = User.objects.filter(is_active=True).values(
            'id', 'username', 'first_name', 'last_name'
        ).order_by('username')

        buildings = Building.objects.all().order_by('name', 'address')
        request_types = RequestType.objects.filter(is_active=True).order_by('name')

        context.update({
            'status_choices': status_choices,
            'executors': executors,
            'priority_choices': priority_choices,
            'selected_status': self.request.GET.get('status'),
            'selected_executor': self.request.GET.get('executor'),
            'selected_priority': self.request.GET.get('priority'),
            'search_query': self.request.GET.get('search', ''),
            'all_users': list(all_users),
            'user_role': role,
            'overdue': self.request.GET.get('overdue'),
            'buildings': buildings,
            'request_types': request_types,
            'filter_data': {
                'building_id': self.request.GET.get('building', ''),
                'request_type': self.request.GET.get('request_type', ''),
                'room_number': self.request.GET.get('room_number', ''),
                'date_from': self.request.GET.get('date_from', ''),
                'date_to': self.request.GET.get('date_to', ''),
            }
        })
        return context


class RequestDetailView(LoginRequiredMixin, DetailView):
    model = ServiceRequest
    template_name = 'requests_app/request_detail.html'
    context_object_name = 'req'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return ServiceRequest.objects.select_related(
            'building', 'section', 'created_by', 'assigned_to'
        ).prefetch_related(
            'files',
            'history',
            'assignees__user',
            'used_materials__material'
        )

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not can_view_request(request.user, self.object):
            messages.error(request, 'У вас нет доступа к этой заявке.')
            return redirect('requests_app:request_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        req = self.object
        user = self.request.user
        role = user.profile.role if hasattr(user, 'profile') else None

        from ..forms import UsedMaterialFormSet
        from .permissions import can_assign_request, can_edit_any_request, can_edit_request

        materials_formset = UsedMaterialFormSet(instance=req)
        can_assign = can_assign_request(user) and req.status in ['new', 'in_progress']
        is_executor = (req.assigned_to == user or req.assignees.filter(user=user).exists())
        can_mark_completed = (is_executor or can_edit_any_request(user)) and req.status == 'in_progress'
        can_suspend = (is_executor or can_edit_any_request(user)) and req.status == 'in_progress'
        can_resume = can_edit_any_request(user) and req.status == 'suspended'
        can_close = can_edit_any_request(user) and req.status == 'completed'
        can_edit = can_edit_request(user, req)

        context.update({
            'request_obj': req,
            'materials_formset': materials_formset,
            'can_assign': can_assign,
            'can_mark_completed': can_mark_completed,
            'can_suspend': can_suspend,
            'can_resume': can_resume,
            'can_close': can_close,
            'can_edit': can_edit,
            'history': req.history.all()[:30],
            'files': req.files.all(),
            'assignees': req.assignees.all(),
        })
        return context


class RequestCreateView(LoginRequiredMixin, CreateView):
    model = ServiceRequest
    form_class = ServiceRequestForm
    template_name = 'requests_app/request_form.html'

    def get_initial(self):
        initial = super().get_initial()
        building_id = self.request.GET.get('building')
        if building_id and building_id.isdigit():
            try:
                from buildings.models import Building
                building = Building.objects.get(pk=int(building_id))
                initial['building'] = building
            except Building.DoesNotExist:
                pass
        else:
            req_settings = RequestSettings.objects.first()
            if req_settings and req_settings.default_building:
                initial['building'] = req_settings.default_building
        return initial

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.request.user, **self.get_form_kwargs())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание заявки'
        return context

    def form_valid(self, form):
        data = form.cleaned_data
        req_settings = RequestSettings.objects.first()
        if req_settings and req_settings.single_building and req_settings.default_building:
            data['building'] = req_settings.default_building
        else:
            data['building'] = data.get('building')
        if not data.get('created_at'):
            data['created_at'] = timezone.now()
        files = self.request.FILES.getlist('files')
        request_obj = RequestService.create_request(data, self.request.user, files)
        messages.success(self.request, f'Заявка {request_obj.request_number} успешно создана.')
        return redirect('requests_app:request_detail', pk=request_obj.pk)

    def form_invalid(self, form):
        messages.error(self.request, 'Ошибка в форме.')
        return super().form_invalid(form)


class RequestUpdateView(LoginRequiredMixin, UpdateView):
    model = ServiceRequest
    form_class = ServiceRequestForm
    template_name = 'requests_app/request_form.html'
    pk_url_kwarg = 'pk'
    context_object_name = 'request_obj'

    def dispatch(self, request, *args, **kwargs):
        if not can_edit_request(request.user, self.get_object()):
            messages.error(request, 'У вас нет прав на редактирование этой заявки.')
            return redirect('requests_app:request_detail', pk=self.get_object().pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.request.user, **self.get_form_kwargs())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Редактирование заявки'
        context['is_edit'] = True
        context['files'] = self.get_object().files.all()
        return context

    def form_valid(self, form):
        data = form.cleaned_data
        req = self.get_object()
        delete_files = self.request.POST.getlist('delete_files')
        new_files = self.request.FILES.getlist('files')
        req = RequestService.update_request(req, data, new_files, delete_files)
        messages.success(self.request, 'Заявка обновлена.')
        return redirect('requests_app:request_detail', pk=req.pk)

    def form_invalid(self, form):
        messages.error(self.request, 'Ошибка в форме.')
        return super().form_invalid(form)


class RequestDeleteView(LoginRequiredMixin, DeleteView):
    model = ServiceRequest
    template_name = 'requests_app/request_confirm_delete.html'
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('requests_app:request_list')

    def dispatch(self, request, *args, **kwargs):
        if not can_delete_request(request.user):
            messages.error(request, 'У вас нет прав на удаление заявок.')
            return redirect('requests_app:request_list')
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        req = self.get_object()
        success, message = RequestService.delete_request(req, request.user)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return redirect(self.success_url)