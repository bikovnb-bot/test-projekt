from django.db import models
from django.contrib.auth.models import User

class Suggestion(models.Model):
    STATUS_CHOICES = (
        ('pending', 'На рассмотрении'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    )
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='suggestions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Предложение"
        verbose_name_plural = "Предложения"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class Bug(models.Model):
    STATUS_CHOICES = (
        ('new', 'Новый'),
        ('in_progress', 'В работе'),
        ('fixed', 'Исправлен'),
        ('closed', 'Закрыт'),
    )
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")
    steps_to_reproduce = models.TextField(blank=True, verbose_name="Шаги воспроизведения")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bugs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Баг"
        verbose_name_plural = "Баги"
        ordering = ['-created_at']

    def __str__(self):
        return self.title