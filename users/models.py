from django.db import models
from django.contrib.auth.models import User, Permission
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.core.validators import RegexValidator
from django.utils import timezone

class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Администратор'
    CONTRACT_SPECIALIST = 'CONTRACT_SPECIALIST', 'Специалист по договорам'
    ENGINEER = 'ENGINEER', 'Инженер'
    DISPATCHER = 'DISPATCHER', 'Диспетчер'
    WORKER = 'WORKER', 'Рабочий'

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.WORKER,
        db_index=True,
        verbose_name='Роль'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(regex=r'^\+?7?\d{10,15}$', message='Введите корректный номер телефона')],
        verbose_name='Телефон'
    )
    position = models.CharField(max_length=100, blank=True, verbose_name='Должность')
    last_activity = models.DateTimeField(null=True, blank=True, verbose_name='Последняя активность')
    login_count = models.IntegerField(default=0, verbose_name='Количество входов')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Аватар')

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_role_display()}"

    def get_all_permissions(self):
        return set(self.user.get_group_permissions())


class UserLogin(models.Model):
    """Модель для хранения истории входов пользователя."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logins')
    login_time = models.DateTimeField(auto_now_add=True, verbose_name='Время входа')
    ip_address = models.GenericIPAddressField(verbose_name='IP-адрес', null=True, blank=True)
    user_agent = models.TextField(verbose_name='User-Agent', blank=True)

    class Meta:
        verbose_name = 'Запись о входе'
        verbose_name_plural = 'История входов'
        ordering = ['-login_time']

    def __str__(self):
        return f"{self.user.username} вошёл {self.login_time.strftime('%d.%m.%Y %H:%M')}"


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance, role=UserRole.WORKER)

@receiver(user_logged_in)
def update_profile_on_login(sender, user, request, **kwargs):
    # Обновление профиля
    if hasattr(user, 'profile'):
        profile = user.profile
        profile.last_activity = timezone.now()
        profile.login_count += 1
        profile.save(update_fields=['last_activity', 'login_count'])

    # Определение реального IP-адреса
    ip = request.META.get('HTTP_X_FORWARDED_FOR')
    if ip:
        ip = ip.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')

    user_agent = request.META.get('HTTP_USER_AGENT', '')

    # Создание записи о входе
    UserLogin.objects.create(user=user, ip_address=ip, user_agent=user_agent)