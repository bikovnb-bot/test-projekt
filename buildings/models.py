# buildings/models.py

import os
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.urls import reverse

def validate_pdf(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext != '.pdf':
        raise ValidationError('Разрешены только PDF-файлы.')
    if value.size > 20 * 1024 * 1024:
        raise ValidationError('Размер файла не должен превышать 20 МБ.')


# buildings/models.py (только класс Building)

class Building(models.Model):
    class BuildingType(models.TextChoices):
        RESIDENTIAL = 'RES', 'Жилое'
        ADMINISTRATIVE = 'ADM', 'Административное'
        PUBLIC = 'PUB', 'Общественное'
        INDUSTRIAL = 'IND', 'Производственное'

    name = models.CharField(max_length=200, verbose_name="Название здания", blank=False, default='')
    cadastral_number = models.CharField(max_length=50, unique=True, verbose_name="Кадастровый номер")
    address = models.CharField(max_length=255, verbose_name="Адрес здания")
    residential_area = models.FloatField(validators=[MinValueValidator(0.0)], default=0.0, verbose_name="Общая площадь жилых помещений (м²)")
    residential_livable_area = models.FloatField(validators=[MinValueValidator(0.0)], default=0.0, verbose_name="Жилая площадь (комнаты, м²)")
    non_residential_area = models.FloatField(validators=[MinValueValidator(0.0)], default=0.0, verbose_name="Площадь нежилых помещений (м²)")
    total_area = models.FloatField(validators=[MinValueValidator(0.0)], verbose_name="Общая площадь здания (м²)", editable=False)
    number_of_floors = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)], verbose_name="Количество этажей")
    year_built = models.PositiveSmallIntegerField(validators=[MinValueValidator(1800), MaxValueValidator(2026)], verbose_name="Год постройки")
    number_of_rooms = models.PositiveIntegerField(default=0, verbose_name="Количество помещений")
    building_type = models.CharField(max_length=3, choices=BuildingType.choices, default=BuildingType.RESIDENTIAL, verbose_name="Тип здания")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    # Паспортные поля
    balance_cost = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name="Балансовая стоимость (млн руб.)")
    territory_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Площадь прилегающей территории (м²)")
    project_type = models.CharField(max_length=100, blank=True, verbose_name="Тип проекта")
    underground_floors = models.PositiveSmallIntegerField(default=0, verbose_name="Количество подземных этажей")
    is_cultural_heritage = models.BooleanField(default=False, verbose_name="Объект культурного наследия")
    emergency_info = models.TextField(blank=True, verbose_name="Сведения об аварийности")
    major_repair_decision = models.TextField(blank=True, verbose_name="Решение о капитальном ремонте")
    demolition_decision = models.TextField(blank=True, verbose_name="Решение о сносе")
    building_volume = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Объем здания (м³)")
    underground_volume = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Объем подземной части (м³)")

    # Конструктивная характеристика
    foundation_desc = models.TextField(blank=True, verbose_name="Фундаменты")
    frame_desc = models.TextField(blank=True, verbose_name="Несущий каркас")
    walls_desc = models.TextField(blank=True, verbose_name="Стены и перегородки")
    floors_desc = models.TextField(blank=True, verbose_name="Междуэтажные и чердачное перекрытия")
    stairs_desc = models.TextField(blank=True, verbose_name="Лестницы")
    roof_structure_desc = models.TextField(blank=True, verbose_name="Несущие элементы кровли")
    roof_cover_desc = models.TextField(blank=True, verbose_name="Кровля (водоизолирующий слой)")

    # Контакты
    director_name = models.CharField(max_length=200, blank=True, verbose_name="ФИО руководителя")
    director_phone = models.CharField(max_length=50, blank=True, verbose_name="Телефон руководителя")
    institution_name = models.CharField(max_length=200, blank=True, verbose_name="Наименование учреждения")

    class Meta:
        verbose_name = "Здание"
        verbose_name_plural = "Здания"
        ordering = ['-year_built', 'address']

    def save(self, *args, **kwargs):
        self.total_area = self.residential_area + self.non_residential_area
        super().save(*args, **kwargs)

    def __str__(self):
        if self.name:
            return self.name
        parts = self.address.split(',')
        if len(parts) >= 2:
            return ', '.join(parts[:2]).strip()
        return self.address.strip()

    def get_absolute_url(self):
        return reverse('buildings:passport_detail', args=[self.pk])


class BuildingSection(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='sections', verbose_name="Здание")
    name = models.CharField(max_length=100, verbose_name="Название части здания")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Порядок")
    is_common = models.BooleanField(default=False, verbose_name="Общая (относится ко всему зданию)")

    class Meta:
        ordering = ['order', 'name']
        unique_together = [['building', 'name']]
        verbose_name = "Часть здания"
        verbose_name_plural = "Части здания"

    def __str__(self):
        return f"{self.building} – {self.name}"


class BuildingDocument(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='documents', verbose_name="Здание")
    section = models.ForeignKey(BuildingSection, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Часть здания")
    file = models.FileField(upload_to='building_documents/%Y/%m/%d/', validators=[validate_pdf], verbose_name="Файл документа (PDF)")
    title = models.CharField(max_length=255, blank=True, verbose_name="Название документа")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        verbose_name = "Документ здания"
        verbose_name_plural = "Документы зданий"
        ordering = ['-uploaded_at']

    def __str__(self):
        if self.title:
            return f"{self.title} ({self.building})"
        return f"Документ от {self.uploaded_at.date()} для {self.building}"


class BuildingOwnershipDocument(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='ownership_docs', verbose_name="Здание")
    title = models.CharField(max_length=255, blank=True, verbose_name="Название документа")
    file = models.FileField(
        upload_to='building_ownership_docs/%Y/%m/',
        validators=[validate_pdf],
        verbose_name="Файл (PDF)"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        verbose_name = "Документ о собственности"
        verbose_name_plural = "Документы о собственности"

    def __str__(self):
        return self.title or f"Документ от {self.uploaded_at.date()}"


class BuildingArea(models.Model):
    AREA_TYPE_CHOICES = [
        ('roof', 'Кровля'),
        ('premises', 'Помещения'),
        ('floor', 'Полы'),
    ]
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='areas', verbose_name="Здание")
    section = models.ForeignKey(BuildingSection, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Часть здания")
    area_type = models.CharField(max_length=20, choices=AREA_TYPE_CHOICES, verbose_name="Тип площади")
    name = models.CharField(max_length=200, verbose_name="Наименование (тип покрытия/помещения)")
    area = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Площадь (м²)")

    class Meta:
        verbose_name = "Площадь здания"
        verbose_name_plural = "Площади здания"

    def __str__(self):
        return f"{self.get_area_type_display()}: {self.name} – {self.area} м²"


class BuildingRoom(models.Model):
    FLOOR_CHOICES = [
        ('basement', 'Подвал'),
        ('1', '1 этаж'),
        ('2', '2 этаж'),
        ('3', '3 этаж'),
        ('4', '4 этаж'),
        ('5', '5 этаж'),
        ('technical', 'Технический этаж'),
        ('attic', 'Чердак'),
    ]
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='rooms', verbose_name="Здание")
    section = models.ForeignKey(BuildingSection, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Часть здания")
    floor = models.CharField(max_length=20, choices=FLOOR_CHOICES, verbose_name="Этаж")
    name = models.CharField(max_length=100, verbose_name="Наименование помещения")
    ceiling_finish = models.CharField(max_length=200, blank=True, verbose_name="Потолок")
    walls_finish = models.CharField(max_length=200, blank=True, verbose_name="Стены")
    floors_finish = models.CharField(max_length=200, blank=True, verbose_name="Полы")
    windows = models.CharField(max_length=200, blank=True, verbose_name="Окна")
    doors = models.CharField(max_length=200, blank=True, verbose_name="Двери")
    last_repair_type = models.CharField(max_length=100, blank=True, verbose_name="Вид ремонта")
    last_repair_year = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Год последнего ремонта")
    condition = models.CharField(max_length=100, blank=True, verbose_name="Общее состояние")
    recommendations = models.TextField(blank=True, verbose_name="Рекомендации")

    class Meta:
        verbose_name = "Внутреннее помещение"
        verbose_name_plural = "Внутренние помещения"

    def __str__(self):
        return f"{self.get_floor_display()}: {self.name}"


class BuildingSystem(models.Model):
    SYSTEM_TYPES = [
        ('heating', 'Теплоснабжение'),
        ('hot_water', 'ГВС'),
        ('cold_water', 'ХВС'),
        ('sewerage', 'Водоотведение и канализация'),
        ('electricity', 'Электроснабжение'),
        ('ventilation', 'Вентиляция'),
        ('fire', 'Противопожарные системы'),
        ('security', 'Охранные системы'),
        ('comms', 'Сети связи и локальные сети'),
        ('other', 'Прочие коммуникации'),
    ]
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='systems', verbose_name="Здание")
    section = models.ForeignKey(BuildingSection, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Часть здания")
    system_type = models.CharField(max_length=20, choices=SYSTEM_TYPES, verbose_name="Тип системы")
    system_type_other = models.CharField(max_length=100, blank=True, verbose_name="Другое (если 'Прочие')")
    type_desc = models.CharField(max_length=200, blank=True, verbose_name="Тип системы (описание)")
    power = models.CharField(max_length=100, blank=True, verbose_name="Мощность (Гкал/ч, кВт и т.п.)")
    inlet_diameter = models.CharField(max_length=50, blank=True, verbose_name="Диаметр ввода")
    district_number = models.CharField(max_length=50, blank=True, verbose_name="№ района")
    district_phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон района")
    subscriber_number = models.CharField(max_length=50, blank=True, verbose_name="№ абонента")
    meter1_type = models.CharField(max_length=50, blank=True, verbose_name="Тип счётчика (1)")
    meter1_number = models.CharField(max_length=50, blank=True, verbose_name="№ счётчика (1)")
    meter1_verification_date = models.DateField(null=True, blank=True, verbose_name="Дата очередной поверки (1)")
    meter2_type = models.CharField(max_length=50, blank=True, verbose_name="Тип счётчика (2)")
    meter2_number = models.CharField(max_length=50, blank=True, verbose_name="№ счётчика (2)")
    meter2_verification_date = models.DateField(null=True, blank=True, verbose_name="Дата очередной поверки (2)")
    meter3_type = models.CharField(max_length=50, blank=True, verbose_name="Тип счётчика (3)")
    meter3_number = models.CharField(max_length=50, blank=True, verbose_name="№ счётчика (3)")
    meter3_verification_date = models.DateField(null=True, blank=True, verbose_name="Дата очередной поверки (3)")
    network_description = models.TextField(blank=True, verbose_name="Краткая характеристика сети")
    last_repair_type = models.CharField(max_length=100, blank=True, verbose_name="Вид ремонта")
    last_repair_year = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Год последнего ремонта")
    installed_power = models.CharField(max_length=100, blank=True, verbose_name="Мощность установленная (кВт) (для электроснабжения)")
    permitted_power = models.CharField(max_length=100, blank=True, verbose_name="Мощность разрешенная (кВт) (для электроснабжения)")

    class Meta:
        verbose_name = "Инженерная система"
        verbose_name_plural = "Инженерные системы"

    def __str__(self):
        return f"{self.get_system_type_display()} – {self.building}"


class BuildingLandscaping(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='landscaping', verbose_name="Здание")
    section = models.ForeignKey(BuildingSection, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Часть здания")
    element = models.CharField(max_length=200, verbose_name="Элемент благоустройства")
    quantity = models.CharField(max_length=100, blank=True, verbose_name="Кол-во, площадь, длина")
    characteristic = models.CharField(max_length=200, blank=True, verbose_name="Характеристика")
    has_documents = models.BooleanField(default=False, verbose_name="Наличие паспортов/сертификатов")
    condition = models.CharField(max_length=200, blank=True, verbose_name="Состояние")
    recommendations = models.TextField(blank=True, verbose_name="Рекомендации")

    class Meta:
        verbose_name = "Элемент благоустройства"
        verbose_name_plural = "Благоустройство территории"

    def __str__(self):
        return self.element


class BuildingInspection(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='inspections', verbose_name="Здание")
    section = models.ForeignKey(BuildingSection, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Часть здания")
    inspection_date = models.DateField(verbose_name="Дата проверки")
    reason = models.CharField(max_length=200, blank=True, verbose_name="Причина проверки")
    inspector = models.CharField(max_length=200, verbose_name="ФИО, должность проверяющего")
    findings = models.TextField(verbose_name="Основные замечания, № предписания")
    conclusion = models.TextField(blank=True, verbose_name="Заключение")
    recommendations = models.TextField(blank=True, verbose_name="Рекомендации")

    class Meta:
        ordering = ['-inspection_date']
        verbose_name = "Проверка"
        verbose_name_plural = "Проверки"

    def __str__(self):
        return f"Проверка от {self.inspection_date}"


class BuildingRepair(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='repairs', verbose_name="Здание")
    section = models.ForeignKey(BuildingSection, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Часть здания")
    object_name = models.CharField(max_length=200, verbose_name="Объект ремонта")
    repair_type = models.CharField(max_length=100, verbose_name="Вид ремонта")
    start_date = models.DateField(verbose_name="Дата начала")
    end_date = models.DateField(verbose_name="Дата окончания")
    contract_number = models.CharField(max_length=50, blank=True, verbose_name="№ контракта")
    contract_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name="Сумма контракта (руб.)")
    contractor = models.CharField(max_length=200, blank=True, verbose_name="Наименование организации")
    warranty_period = models.CharField(max_length=100, blank=True, verbose_name="Гарантийный срок")
    note = models.TextField(blank=True, verbose_name="Примечание")

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Ремонт"
        verbose_name_plural = "Ремонты"

    def __str__(self):
        return f"{self.object_name} – {self.repair_type} ({self.start_date})"


class BuildingTenant(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='tenants', verbose_name="Здание")
    section = models.ForeignKey(BuildingSection, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Часть здания")
    name = models.CharField(max_length=200, verbose_name="Наименование арендатора")
    activity = models.CharField(max_length=200, blank=True, verbose_name="Вид деятельности")
    rented_areas = models.CharField(max_length=200, blank=True, verbose_name="Арендуемая площадь (номера помещений)")
    lease_term = models.CharField(max_length=100, blank=True, verbose_name="Срок аренды")
    contract_number = models.CharField(max_length=100, blank=True, verbose_name="Номер договора аренды")

    class Meta:
        verbose_name = "Арендатор"
        verbose_name_plural = "Арендаторы"

    def __str__(self):
        return self.name


class BuildingAppendix(models.Model):
    APPENDIX_TYPES = [
        ('geobase', 'Геоподоснова'),
        ('bti_plan', 'Планы БТИ'),
        ('explication', 'Экспликация'),
        ('other', 'Другое'),
    ]
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='appendixes', verbose_name="Здание")
    section = models.ForeignKey(BuildingSection, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Часть здания")
    appendix_type = models.CharField(max_length=20, choices=APPENDIX_TYPES, verbose_name="Тип приложения")
    title = models.CharField(max_length=255, blank=True, verbose_name="Название")
    file = models.FileField(upload_to='building_appendixes/%Y/%m/', validators=[validate_pdf], verbose_name="Файл (PDF)")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        verbose_name = "Приложение"
        verbose_name_plural = "Приложения"

    def __str__(self):
        return f"{self.get_appendix_type_display()}: {self.title or self.file.name}"