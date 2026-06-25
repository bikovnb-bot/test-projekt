# users/tests.py
# -*- coding: utf-8 -*-

"""
Тесты для приложения users.
Покрывают модели, контекстные процессоры, декораторы и представления.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User, Permission, Group
from django.urls import reverse

from .models import Profile, UserRole, UserLogin
from .decorators import role_required


# ----------------------------------------------------------------------
# Тесты моделей
# ----------------------------------------------------------------------

class ProfileModelTest(TestCase):
    """Тесты для модели Profile."""

    def setUp(self):
        """Создаём тестового пользователя и группу с правами."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        # Профиль создаётся сигналом, но для надёжности используем get_or_create
        Profile.objects.get_or_create(user=self.user, defaults={'role': UserRole.WORKER})

        # Создаём группу и добавляем право
        self.group = Group.objects.create(name='testgroup')
        self.perm = Permission.objects.get(codename='add_logentry')
        self.group.permissions.add(self.perm)
        self.user.groups.add(self.group)

    def test_profile_created_on_user_creation(self):
        """Проверяем, что профиль создаётся автоматически при создании пользователя."""
        # Создаём нового пользователя
        new_user = User.objects.create_user(username='newuser', password='pass')
        self.assertTrue(hasattr(new_user, 'profile'))
        self.assertEqual(new_user.profile.role, UserRole.WORKER)

    def test_get_all_permissions(self):
        """Метод get_all_permissions должен возвращать права пользователя."""
        perms = self.user.profile.get_all_permissions()
        self.assertIn('admin.add_logentry', perms)

    def test_profile_str_method(self):
        """Проверяем строковое представление профиля."""
        self.user.first_name = 'Test'
        self.user.last_name = 'User'
        self.user.save()
        expected = f"{self.user.get_full_name()} - {self.user.profile.get_role_display()}"
        self.assertEqual(str(self.user.profile), expected)


class UserLoginModelTest(TestCase):
    """Тесты для модели UserLogin (история входов)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        Profile.objects.get_or_create(user=self.user, defaults={'role': UserRole.WORKER})
        # Создаём запись входа вручную (сигнал мы не вызываем)
        UserLogin.objects.create(
            user=self.user,
            ip_address='127.0.0.1',
            user_agent='Mozilla/5.0'
        )

    def test_userlogin_creation(self):
        """Проверяем, что запись создаётся корректно."""
        login = UserLogin.objects.get(user=self.user)
        self.assertEqual(login.ip_address, '127.0.0.1')
        self.assertEqual(login.user_agent, 'Mozilla/5.0')
        self.assertIsNotNone(login.login_time)

    def test_userlogin_str_method(self):
        """Строковое представление записи."""
        login = UserLogin.objects.get(user=self.user)
        expected = f"{self.user.username} вошёл {login.login_time.strftime('%d.%m.%Y %H:%M')}"
        self.assertEqual(str(login), expected)


# ----------------------------------------------------------------------
# Тесты контекстных процессоров
# ----------------------------------------------------------------------

class ContextProcessorTest(TestCase):
    """Тесты для контекстных процессоров из context_processors.py."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        Profile.objects.get_or_create(user=self.user, defaults={'role': UserRole.WORKER})

    def test_user_role_for_anonymous(self):
        """Для анонимного пользователя все флаги должны быть False, user_role = None."""
        response = self.client.get(reverse('users:login'))
        self.assertEqual(response.status_code, 200)
        context = response.context
        # Проверяем, что ключ user_role присутствует и равен None
        self.assertIn('user_role', context)
        self.assertIsNone(context.get('user_role'))
        # Флаги должны быть False
        self.assertFalse(context.get('is_admin', False))
        self.assertFalse(context.get('is_contract_specialist', False))
        self.assertFalse(context.get('is_engineer', False))
        self.assertFalse(context.get('is_dispatcher', False))
        self.assertFalse(context.get('is_worker', False))
        self.assertFalse(context.get('is_manager', False))
        self.assertFalse(context.get('is_viewer', False))
        self.assertFalse(context.get('is_contractor', False))

    def test_user_permissions(self):
        """Проверяем, что процессор user_permissions добавляет права."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 200)
        context = response.context
        # В контексте должен быть ключ user_permissions
        self.assertIn('user_permissions', context)
        self.assertIsInstance(context['user_permissions'], set)
        # У пользователя есть право add_logentry через группу
        self.assertIn('admin.add_logentry', context['user_permissions'])


# ----------------------------------------------------------------------
# Тесты декораторов
# ----------------------------------------------------------------------

class DecoratorTest(TestCase):
    """Тесты декораторов ролей."""

    def setUp(self):
        self.client = Client()
        # Создаём суперпользователя
        self.admin = User.objects.create_superuser(
            username='admin',
            password='adminpass'
        )
        # Профиль для суперпользователя создаётся сигналом
        # Создаём обычного рабочего
        self.worker = User.objects.create_user(
            username='worker',
            password='workerpass'
        )
        Profile.objects.get_or_create(user=self.worker, defaults={'role': UserRole.WORKER})
        # Создаём пользователя с ролью инженера
        self.engineer = User.objects.create_user(
            username='engineer',
            password='engineerpass'
        )
        Profile.objects.get_or_create(user=self.engineer, defaults={'role': UserRole.ENGINEER})

    def test_role_required_decorator_allows_admin(self):
        """Администратор имеет доступ ко всем страницам."""
        self.client.login(username='admin', password='adminpass')
        response = self.client.get(reverse('users:user_list'))
        self.assertEqual(response.status_code, 200)

    def test_role_required_decorator_denies_worker(self):
        """Рабочий не имеет доступа к админским страницам."""
        self.client.login(username='worker', password='workerpass')
        response = self.client.get(reverse('users:user_list'))
        self.assertEqual(response.status_code, 403)

    def test_role_required_decorator_allows_engineer_for_contract_access(self):
        """Инженер имеет доступ к просмотру договоров (contract_access_required)."""
        from django.http import HttpResponse

        @role_required([UserRole.ADMIN, UserRole.CONTRACT_SPECIALIST, UserRole.ENGINEER])
        def dummy_view(request):
            return HttpResponse('OK')

        self.client.login(username='engineer', password='engineerpass')
        request = self.client.get('/').wsgi_request
        request.user = self.engineer
        response = dummy_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'OK')


# ----------------------------------------------------------------------
# Тесты представлений
# ----------------------------------------------------------------------

class ViewsTest(TestCase):
    """Тесты для основных представлений приложения."""

    def setUp(self):
        self.client = Client()
        # Суперпользователь для доступа к админке
        self.admin = User.objects.create_superuser(
            username='admin',
            password='adminpass'
        )
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        Profile.objects.get_or_create(user=self.user, defaults={'role': UserRole.WORKER})

    def test_user_list_requires_login(self):
        """Страница списка пользователей требует аутентификации."""
        response = self.client.get(reverse('users:user_list'))
        self.assertEqual(response.status_code, 302)  # редирект на логин

    def test_user_list_accessible_to_admin(self):
        """Администратор может просматривать список."""
        self.client.login(username='admin', password='adminpass')
        response = self.client.get(reverse('users:user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_obj', response.context)

    def test_user_list_uses_pagination(self):
        """Проверяем, что пагинация работает (25 записей на страницу)."""
        self.client.login(username='admin', password='adminpass')
        # Создаём 30 пользователей (один уже есть)
        for i in range(30):
            User.objects.create_user(username=f'test{i}', password='pass')
        response = self.client.get(reverse('users:user_list'))
        self.assertEqual(response.status_code, 200)
        page_obj = response.context['page_obj']
        self.assertEqual(len(page_obj), 25)  # на первой странице 25

    def test_user_create_view(self):
        """Тест создания пользователя."""
        self.client.login(username='admin', password='adminpass')
        response = self.client.get(reverse('users:user_create'))
        self.assertEqual(response.status_code, 200)
        # POST с данными
        data = {
            'username': 'newuser',
            'password': 'strongpass123',
            'password_confirm': 'strongpass123',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@example.com',
            'role': UserRole.ENGINEER,
            'phone': '+79991234567',
            'position': 'Тестировщик',
        }
        response = self.client.post(reverse('users:user_create'), data, follow=True)
        self.assertRedirects(response, reverse('users:user_list'))
        self.assertTrue(User.objects.filter(username='newuser').exists())
        user = User.objects.get(username='newuser')
        self.assertEqual(user.profile.role, UserRole.ENGINEER)

    def test_user_edit_view(self):
        """Тест редактирования пользователя."""
        self.client.login(username='admin', password='adminpass')
        user = User.objects.create_user(username='edituser', password='pass')
        Profile.objects.get_or_create(user=user, defaults={'role': UserRole.WORKER})
        url = reverse('users:user_edit', args=[user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Отправляем изменения
        data = {
            'username': 'edituser',  # не меняем
            'first_name': 'Edited',
            'last_name': 'User',
            'email': 'edited@example.com',
            'is_active': True,
            'groups': [],
            'role': UserRole.ADMIN,
            'phone': '+79998887766',
            'position': 'Admin',
        }
        response = self.client.post(url, data, follow=True)
        self.assertRedirects(response, reverse('users:user_list'))
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Edited')
        self.assertEqual(user.profile.role, UserRole.ADMIN)

    def test_user_delete_view(self):
        """Тест удаления пользователя."""
        self.client.login(username='admin', password='adminpass')
        user = User.objects.create_user(username='deleteuser', password='pass')
        Profile.objects.get_or_create(user=user, defaults={'role': UserRole.WORKER})
        url = reverse('users:user_delete', args=[user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # POST - удаление
        response = self.client.post(url, follow=True)
        self.assertRedirects(response, reverse('users:user_list'))
        self.assertFalse(User.objects.filter(username='deleteuser').exists())

    def test_toggle_active(self):
        """Тест переключения статуса активности."""
        self.client.login(username='admin', password='adminpass')
        user = User.objects.create_user(username='toggleuser', password='pass')
        Profile.objects.get_or_create(user=user, defaults={'role': UserRole.WORKER})
        self.assertTrue(user.is_active)
        url = reverse('users:user_toggle_active', args=[user.id])
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, reverse('users:user_list'))
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        # Повторно включаем
        response = self.client.get(url, follow=True)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_bulk_action_delete(self):
        """Массовое удаление пользователей."""
        self.client.login(username='admin', password='adminpass')
        users = []
        for i in range(3):
            u = User.objects.create_user(username=f'bulk{i}', password='pass')
            Profile.objects.get_or_create(user=u, defaults={'role': UserRole.WORKER})
            users.append(u)
        user_ids = [str(u.id) for u in users]
        data = {
            'action': 'delete',
            'user_ids': user_ids,
        }
        response = self.client.post(reverse('users:bulk_action'), data, follow=True)
        self.assertRedirects(response, reverse('users:user_list'))
        for u in users:
            self.assertFalse(User.objects.filter(id=u.id).exists())

    def test_bulk_action_change_role(self):
        """Массовая смена роли."""
        self.client.login(username='admin', password='adminpass')
        users = []
        for i in range(2):
            u = User.objects.create_user(username=f'bulkrole{i}', password='pass')
            Profile.objects.get_or_create(user=u, defaults={'role': UserRole.WORKER})
            users.append(u)
        user_ids = [str(u.id) for u in users]
        data = {
            'action': 'change_role',
            'user_ids': user_ids,
            'new_role': UserRole.ENGINEER,
        }
        response = self.client.post(reverse('users:bulk_action'), data, follow=True)
        self.assertRedirects(response, reverse('users:user_list'))
        for u in users:
            u.refresh_from_db()
            self.assertEqual(u.profile.role, UserRole.ENGINEER)

    def test_profile_view(self):
        """Тест страницы профиля."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('password_form', response.context)
        self.assertIn('logins', response.context)
        self.assertIn('total_logins', response.context)

    def test_profile_change_password(self):
        """Смена пароля через профиль."""
        self.client.login(username='testuser', password='testpass')
        data = {
            'change_password': '1',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
        }
        response = self.client.post(reverse('users:profile'), data, follow=True)
        # После смены пароля редирект на логин
        self.assertRedirects(response, reverse('users:login'))
        # Проверяем, что новый пароль работает
        self.client.logout()
        login_ok = self.client.login(username='testuser', password='newpass123')
        self.assertTrue(login_ok)

    def test_group_views(self):
        """Тест CRUD групп."""
        self.client.login(username='admin', password='adminpass')
        # Создание группы
        data = {
            'name': 'Test Group',
            'permissions': [Permission.objects.first().id],
        }
        response = self.client.post(reverse('users:group_create'), data, follow=True)
        self.assertRedirects(response, reverse('users:group_list'))
        group = Group.objects.get(name='Test Group')
        # Редактирование
        data['name'] = 'Updated Group'
        response = self.client.post(
            reverse('users:group_edit', args=[group.id]),
            data,
            follow=True
        )
        self.assertRedirects(response, reverse('users:group_list'))
        group.refresh_from_db()
        self.assertEqual(group.name, 'Updated Group')
        # Удаление
        response = self.client.post(
            reverse('users:group_delete', args=[group.id]),
            follow=True
        )
        self.assertRedirects(response, reverse('users:group_list'))
        self.assertFalse(Group.objects.filter(id=group.id).exists())

    def test_role_help_view(self):
        """Страница помощи по ролям доступна админу."""
        self.client.login(username='admin', password='adminpass')
        response = self.client.get(reverse('users:role_help'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('roles_info', response.context)