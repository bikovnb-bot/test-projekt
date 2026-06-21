# requests_app/tests.py
"""
Полный набор тестов для приложения requests_app.
"""

import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.http import HttpResponse
from openpyxl import Workbook

from buildings.models import Building, BuildingSection
from users.models import UserRole, Profile
from requests_app.models import (
    ServiceRequest, RequestType, RequestFile, RequestHistory,
    RequestAssignee, Material, UsedMaterial, RequestSettings
)
from requests_app.forms import ServiceRequestForm, PublicRequestForm, ReportForm, MaterialForm
from requests_app.services import RequestService, MaterialService


class BaseTestCase(TestCase):
    def setUp(self):
        self.building = Building.objects.create(
            name="Тестовое здание",
            cadastral_number="77:01:0000001:1",
            address="г. Москва, ул. Тестовая, д.1",
            residential_area=800.0,
            non_residential_area=200.0,
            number_of_floors=5,
            year_built=2000,
        )
        self.section = BuildingSection.objects.create(
            building=self.building,
            name="Тестовая секция"
        )
        self.request_type = RequestType.objects.create(
            name="Тестовый тип",
            is_active=True
        )
        self.admin_user = self._create_user_with_role('admin', UserRole.ADMIN)
        self.manager_user = self._create_user_with_role('manager', UserRole.ENGINEER)
        self.worker_user = self._create_user_with_role('worker', UserRole.WORKER)
        self.client = Client()

    def _create_user_with_role(self, username, role):
        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password('testpass123')
            user.save()
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()
        return user

    def create_request(self, **kwargs):
        defaults = {
            'building': self.building,
            'section': self.section,
            'room_number': '101',
            'request_type': self.request_type,
            'description': 'Тестовая заявка',
            'priority': 'medium',
            'status': 'new',
            'created_by': self.worker_user,
        }
        defaults.update(kwargs)
        return ServiceRequest.objects.create(**defaults)


class RequestModelTest(BaseTestCase):
    def test_request_number_auto_generation(self):
        req = self.create_request()
        self.assertTrue(req.request_number.startswith("ЗЯ-"))
        self.assertGreaterEqual(len(req.request_number), 8)

    def test_get_creator_display_with_user(self):
        req = self.create_request()
        self.assertEqual(req.get_creator_display(), self.worker_user.username)

    def test_get_creator_display_with_contact(self):
        req = self.create_request(created_by=None, contact_name="Иван Петров")
        self.assertEqual(req.get_creator_display(), "Иван Петров")

    def test_get_creator_display_public(self):
        req = self.create_request(created_by=None, contact_name=None)
        self.assertEqual(req.get_creator_display(), "Публичная")

    def test_return_materials_to_stock(self):
        material = Material.objects.create(name="Краска", unit="л", default_price=100, quantity_in_stock=50)
        req = self.create_request()
        UsedMaterial.objects.create(
            request=req,
            material=material,
            name=material.name,
            quantity=5,
            unit=material.unit,
            price_per_unit=100,
            total_price=500
        )
        req.return_materials_to_stock()
        material.refresh_from_db()
        self.assertEqual(material.quantity_in_stock, 55)

    def test_status_choices(self):
        self.assertEqual(len(ServiceRequest.STATUS_CHOICES), 5)


class MaterialModelTest(BaseTestCase):
    def test_str(self):
        material = Material.objects.create(name="Гвозди", unit="кг", default_price=50, quantity_in_stock=10)
        self.assertEqual(str(material), "Гвозди (кг)")

    def test_used_material_total_price(self):
        material = Material.objects.create(name="Краска", unit="л", default_price=100, quantity_in_stock=10)
        req = self.create_request()
        used = UsedMaterial.objects.create(
            request=req,
            material=material,
            name=material.name,
            quantity=2.5,
            unit="л",
            price_per_unit=100,
        )
        used.save()
        self.assertEqual(used.total_price, 250)


class RequestHistoryModelTest(BaseTestCase):
    def test_str(self):
        req = self.create_request()
        history = RequestHistory.objects.create(
            request=req,
            user=self.admin_user,
            action="Тестовое действие"
        )
        self.assertIn(req.request_number, str(history))


class ServiceRequestFormTest(BaseTestCase):
    def test_valid_form(self):
        data = {
            'building': self.building.id,
            'section': self.section.id,
            'room_number': '101',
            'request_type': self.request_type.id,
            'description': 'Тестовое описание',
            'priority': 'high',
        }
        form = ServiceRequestForm(self.worker_user, data)
        self.assertTrue(form.is_valid())

    def test_missing_required_fields(self):
        data = {
            'building': '',
            'room_number': '',
            'request_type': '',
            'description': '',
        }
        form = ServiceRequestForm(self.worker_user, data)
        self.assertFalse(form.is_valid())
        self.assertIn('building', form.errors)
        self.assertIn('room_number', form.errors)
        self.assertIn('request_type', form.errors)
        self.assertIn('description', form.errors)


class PublicRequestFormTest(BaseTestCase):
    def test_valid_form(self):
        data = {
            'building': self.building.id,
            'section': self.section.id,
            'room_number': '101',
            'request_type': self.request_type.id,
            'description': 'Тест',
            'contact_name': 'Иван',
            'contact_phone': '+7 999 123-45-67',
            'captcha_answer': 5,
            'captcha_num1': 2,
            'captcha_num2': 3,
            'captcha_operator': '+',
        }
        form = PublicRequestForm(data)
        self.assertTrue(form.is_valid())

    def test_invalid_captcha(self):
        data = {
            'building': self.building.id,
            'room_number': '101',
            'request_type': self.request_type.id,
            'description': 'test',
            'captcha_answer': 10,
            'captcha_num1': 2,
            'captcha_num2': 3,
            'captcha_operator': '+',
        }
        form = PublicRequestForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('captcha_answer', form.errors)


class ReportFormTest(BaseTestCase):
    def test_valid_form(self):
        data = {
            'columns': ['request_number', 'building', 'status'],
            'status': 'new',
            'priority': 'high',
        }
        form = ReportForm(data)
        self.assertTrue(form.is_valid())

    def test_empty_form(self):
        form = ReportForm({})
        self.assertTrue(form.is_valid())


class RequestServiceTest(BaseTestCase):
    def test_create_request(self):
        data = {
            'building': self.building,
            'section': self.section,
            'room_number': '101',
            'request_type': self.request_type,
            'description': 'Тест',
            'priority': 'medium',
        }
        req = RequestService.create_request(data, self.worker_user)
        self.assertIsNotNone(req.pk)
        self.assertEqual(req.status, 'new')
        self.assertEqual(req.created_by, self.worker_user)

    def test_update_request(self):
        req = self.create_request()
        data = {'description': 'Новое описание'}
        updated = RequestService.update_request(req, data)
        self.assertEqual(updated.description, 'Новое описание')

    def test_assign_executor(self):
        req = self.create_request(status='new')
        success, msg = RequestService.assign_executor(req, self.manager_user.id, self.admin_user)
        self.assertTrue(success)
        self.assertEqual(req.status, 'in_progress')
        self.assertEqual(req.assigned_to, self.manager_user)

    def test_mark_completed(self):
        req = self.create_request(status='in_progress', assigned_to=self.worker_user)
        success, msg = RequestService.mark_completed(req, self.worker_user)
        self.assertTrue(success)
        self.assertEqual(req.status, 'completed')
        self.assertIsNotNone(req.completed_date)

    def test_suspend_request(self):
        req = self.create_request(status='in_progress')
        success, msg = RequestService.suspend_request(req, self.admin_user, 'Тестовая причина')
        self.assertTrue(success)
        self.assertEqual(req.status, 'suspended')
        self.assertEqual(req.suspension_reason, 'Тестовая причина')

    def test_resume_request(self):
        req = self.create_request(status='suspended')
        success, msg = RequestService.resume_request(req, self.admin_user)
        self.assertTrue(success)
        self.assertEqual(req.status, 'in_progress')

    def test_close_request_with_materials(self):
        req = self.create_request(status='completed')
        material = Material.objects.create(name="Тест", unit="шт", default_price=10, quantity_in_stock=100)
        materials_data = [
            {'material_id': material.id, 'quantity': 5, 'unit': 'шт', 'price_per_unit': 10}
        ]
        success, msg = RequestService.close_request(req, self.admin_user, materials_data)
        self.assertTrue(success)
        self.assertEqual(req.status, 'closed')
        material.refresh_from_db()
        self.assertEqual(material.quantity_in_stock, 95)

    def test_close_request_insufficient_materials(self):
        req = self.create_request(status='completed')
        material = Material.objects.create(name="Тест", unit="шт", default_price=10, quantity_in_stock=5)
        materials_data = [
            {'material_id': material.id, 'quantity': 10, 'unit': 'шт', 'price_per_unit': 10}
        ]
        success, msg = RequestService.close_request(req, self.admin_user, materials_data)
        self.assertFalse(success)
        self.assertIn('Недостаточно материала', msg)

    def test_add_assignee(self):
        req = self.create_request()
        user2 = self._create_user_with_role('worker2', UserRole.WORKER)
        success, msg = RequestService.add_assignee(req, self.admin_user, user2.id)
        self.assertTrue(success)
        self.assertTrue(RequestAssignee.objects.filter(request=req, user=user2).exists())

    def test_remove_assignee(self):
        req = self.create_request()
        user2 = self._create_user_with_role('worker2', UserRole.WORKER)
        RequestAssignee.objects.create(request=req, user=user2)
        success, msg = RequestService.remove_assignee(req, self.admin_user, user2.id)
        self.assertTrue(success)
        self.assertFalse(RequestAssignee.objects.filter(request=req, user=user2).exists())


class MaterialServiceTest(BaseTestCase):
    def test_create_material(self):
        data = {'name': 'Новый материал', 'unit': 'кг', 'default_price': 50, 'quantity_in_stock': 10}
        material = MaterialService.create_material(data)
        self.assertEqual(material.name, 'Новый материал')

    def test_update_material(self):
        material = Material.objects.create(name="Старый", unit="кг", default_price=10, quantity_in_stock=5)
        data = {'name': 'Новое имя'}
        updated = MaterialService.update_material(material, data)
        self.assertEqual(updated.name, 'Новое имя')

    def test_reduce_stock(self):
        material = Material.objects.create(name="Тест", unit="шт", default_price=10, quantity_in_stock=10)
        MaterialService.reduce_stock(material, 3)
        material.refresh_from_db()
        self.assertEqual(material.quantity_in_stock, 7)

    def test_reduce_stock_insufficient(self):
        material = Material.objects.create(name="Тест", unit="шт", default_price=10, quantity_in_stock=2)
        with self.assertRaises(ValueError):
            MaterialService.reduce_stock(material, 5)


class RequestViewsTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='testpass123')

    def test_request_list_view(self):
        response = self.client.get(reverse('requests_app:request_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requests_app/request_list.html')

    def test_request_create_view_get(self):
        response = self.client.get(reverse('requests_app:request_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requests_app/request_form.html')

    def test_request_create_view_post(self):
        data = {
            'building': self.building.id,
            'section': self.section.id,
            'room_number': '101',
            'request_type': self.request_type.id,
            'description': 'Новая заявка',
            'priority': 'high',
        }
        response = self.client.post(reverse('requests_app:request_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ServiceRequest.objects.filter(description='Новая заявка').exists())

    def test_request_detail_view(self):
        req = self.create_request()
        response = self.client.get(reverse('requests_app:request_detail', args=[req.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requests_app/request_detail.html')

    def test_request_edit_view_get(self):
        req = self.create_request()
        response = self.client.get(reverse('requests_app:request_edit', args=[req.pk]))
        self.assertEqual(response.status_code, 200)

    def test_request_edit_view_post(self):
        req = self.create_request()
        data = {
            'building': req.building.id,
            'section': req.section.id if req.section else '',
            'room_number': '202',
            'request_type': req.request_type.id,
            'description': 'Обновленное описание',
            'priority': req.priority,
        }
        response = self.client.post(reverse('requests_app:request_edit', args=[req.pk]), data)
        self.assertEqual(response.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.room_number, '202')
        self.assertEqual(req.description, 'Обновленное описание')

    def test_request_delete_view_get(self):
        req = self.create_request()
        response = self.client.get(reverse('requests_app:request_delete', args=[req.pk]))
        self.assertEqual(response.status_code, 200)

    def test_request_delete_view_post(self):
        req = self.create_request()
        response = self.client.post(reverse('requests_app:request_delete', args=[req.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ServiceRequest.objects.filter(pk=req.pk).exists())

    def test_request_assign(self):
        req = self.create_request(status='new')
        data = {'assigned_to': self.worker_user.id}
        response = self.client.post(reverse('requests_app:request_assign', args=[req.pk]), data)
        self.assertEqual(response.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.assigned_to, self.worker_user)
        self.assertEqual(req.status, 'in_progress')

    def test_request_mark_completed(self):
        req = self.create_request(status='in_progress', assigned_to=self.worker_user)
        response = self.client.post(reverse('requests_app:request_complete', args=[req.pk]), {'time_spent': 30})
        self.assertEqual(response.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, 'completed')
        self.assertEqual(req.time_spent, 30)

    def test_request_suspend(self):
        req = self.create_request(status='in_progress')
        response = self.client.post(reverse('requests_app:request_suspend', args=[req.pk]), {'suspension_reason': 'Тест'})
        self.assertEqual(response.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, 'suspended')
        self.assertEqual(req.suspension_reason, 'Тест')

    def test_request_resume(self):
        req = self.create_request(status='suspended')
        response = self.client.post(reverse('requests_app:request_resume', args=[req.pk]))
        self.assertEqual(response.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, 'in_progress')

    def test_request_close(self):
        material = Material.objects.create(name="Тест", unit="шт", default_price=10, quantity_in_stock=10)
        req = self.create_request(status='completed')
        data = {
            'material_id[]': [material.id],
            'material_quantity[]': [5],
            'material_unit[]': ['шт'],
            'material_price[]': [10],
        }
        response = self.client.post(reverse('requests_app:request_close', args=[req.pk]), data)
        self.assertEqual(response.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, 'closed')
        self.assertTrue(UsedMaterial.objects.filter(request=req).exists())

    def test_dashboard_view(self):
        response = self.client.get(reverse('requests_app:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requests_app/dashboard.html')

    def test_export_excel(self):
        self.create_request()
        response = self.client.get(reverse('requests_app:export_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


class AjaxTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='testpass123')

    def test_api_building_sections(self):
        response = self.client.get(reverse('requests_app:api_building_sections'), {'building_id': self.building.id})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], self.section.name)

    def test_api_overdue_requests(self):
        req = self.create_request(
            status='in_progress',
            planned_date=datetime.date.today() - datetime.timedelta(days=5),
            assigned_to=self.worker_user
        )
        response = self.client.get(reverse('requests_app:api_overdue_requests'), {'assignee_id': self.worker_user.id})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['requests']), 1)
        self.assertEqual(data['requests'][0]['request_number'], req.request_number)


class PublicRequestTest(BaseTestCase):
    def test_public_form_get(self):
        response = self.client.get(reverse('requests_app:public_request_create') + '?lang=ru')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requests_app/public_request_form_ru.html')

    def test_public_form_post_valid(self):
        data = {
            'building': self.building.id,
            'section': self.section.id,
            'room_number': '101',
            'request_type': self.request_type.id,
            'description': 'Публичная заявка',
            'contact_name': 'Иван',
            'contact_phone': '+7 999 123-45-67',
            'captcha_answer': 5,
        }
        with patch('requests_app.views.public.send_telegram_notification'):
            with patch('requests_app.views.utils.generate_new_captcha', return_value={'captcha_num1': 2, 'captcha_num2': 3, 'captcha_operator': '+'}):
                response = self.client.post(reverse('requests_app:public_request_create') + '?lang=ru', data)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(ServiceRequest.objects.filter(description='Публичная заявка').exists())

    def test_public_form_post_invalid_captcha(self):
        data = {
            'building': self.building.id,
            'room_number': '101',
            'request_type': self.request_type.id,
            'description': 'test',
            'captcha_answer': 10,
        }
        with patch('requests_app.views.utils.generate_new_captcha', return_value={'captcha_num1': 2, 'captcha_num2': 3, 'captcha_operator': '+'}):
            response = self.client.post(reverse('requests_app:public_request_create') + '?lang=ru', data)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Неверный ответ')


class UtilsTest(TestCase):
    def test_parse_date(self):
        from requests_app.views.utils import parse_date
        self.assertEqual(parse_date('15.01.2025'), datetime.date(2025, 1, 15))
        self.assertEqual(parse_date('2025-01-15'), datetime.date(2025, 1, 15))
        self.assertEqual(parse_date(None), None)

    def test_parse_datetime(self):
        from requests_app.views.utils import parse_datetime
        self.assertIsNotNone(parse_datetime('2025-01-15 10:30:00'))
        self.assertIsNone(parse_datetime('invalid'))

    def test_generate_new_captcha(self):
        from requests_app.views.utils import generate_new_captcha
        captcha = generate_new_captcha()
        self.assertIn('captcha_num1', captcha)
        self.assertIn('captcha_num2', captcha)
        self.assertIn('captcha_operator', captcha)

    @patch('requests_app.views.utils.cache')
    def test_rate_limit(self, mock_cache):
        from requests_app.views.utils import rate_limit
        mock_cache.get.return_value = 5
        @rate_limit(limit=5)
        def dummy_view(request):
            return HttpResponse("OK")
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        mock_cache.get.return_value = 10
        response = dummy_view(request)
        self.assertEqual(response.status_code, 403)