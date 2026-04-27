import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="profile", on_delete=models.CASCADE
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    free_recognitions_used = models.IntegerField(
        default=0, verbose_name="Використано безкоштовних розпізнавань"
    )

    def __str__(self):
        return f"Профіль: {self.user.username}"


class Camera(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва камери")
    location = models.CharField(max_length=255, blank=True, verbose_name="Розташування")
    stream_url = models.CharField(max_length=255, verbose_name="Потік (IP/URL)")
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=255, verbose_name="Назва підрозділу")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subsections",
        verbose_name="Входить до підрозділу",
    )

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} -> {self.name}"
        return self.name

    class Meta:
        verbose_name = "Підрозділ"
        verbose_name_plural = "Підрозділи"


class Employee(models.Model):
    photo = models.ImageField(upload_to="employees/", null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, verbose_name="Підрозділ"
    )
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "Працівник"
        verbose_name_plural = "Працівники"


class Vehicle(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="vehicles",
        verbose_name="Співробітник",
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Зареєстрував (Користувач)",
    )

    plate_text = models.CharField(max_length=20, unique=True, verbose_name="Номер авто")
    brand_model = models.CharField(
        max_length=100, blank=True, verbose_name="Марка/Модель"
    )

    owner_first_name = models.CharField(
        max_length=50, verbose_name="Ім'я власника", default="Гість"
    )
    owner_last_name = models.CharField(
        max_length=50, verbose_name="Прізвище власника", default="Невідомо"
    )

    def __str__(self):
        if self.employee:
            return f"{self.plate_text} ({self.employee.last_name} {self.employee.first_name})"
        return f"{self.plate_text} ({self.owner_last_name} {self.owner_first_name})"


class AccessPermit(models.Model):
    vehicle = models.OneToOneField(
        Vehicle, on_delete=models.CASCADE, verbose_name="Автомобіль"
    )
    is_allowed = models.BooleanField(default=True, verbose_name="Дозвіл")
    end_date = models.DateField(null=True, blank=True, verbose_name="Дійсний до")

    def __str__(self):
        return f"Дозвіл {self.vehicle.plate_text}"


class BlackList(models.Model):
    plate_text = models.CharField(
        max_length=20, unique=True, verbose_name="Номер у чорному списку"
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата додавання")

    class Meta:
        verbose_name = "Чорний список"
        verbose_name_plural = "Чорний список"

    def __str__(self):
        return f"BLOCK: {self.plate_text}"


class DetectedPlate(models.Model):
    camera = models.ForeignKey(
        Camera, on_delete=models.SET_NULL, null=True, verbose_name="Камера"
    )
    plate_text = models.CharField(max_length=20, verbose_name="Розпізнаний номер")

    vehicle = models.ForeignKey(
        "Vehicle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detections",
        verbose_name="Розпізнане авто",
    )

    image = models.ImageField(
        upload_to="detections/%Y/%m/%d/",
        verbose_name="Фото фіксації",
        null=True,
        blank=True,
    )
    confidence = models.FloatField(verbose_name="Впевненість")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Час події")

    class Meta:
        verbose_name = "Розпізнаний номер"
        verbose_name_plural = "Розпізнані номери"
        ordering = ["-timestamp"]

    @property
    def is_known(self):
        return self.vehicle is not None

    def __str__(self):
        return f"{self.plate_text} - {self.timestamp.strftime('%H:%M:%S')}"


class APIKey(models.Model):
    PLAN_CHOICES = [
        ("1_month", "1 місяць"),
        ("3_months", "3 місяці"),
        ("1_year", "1 рік"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_active = models.BooleanField(default=True)
    requests_limit = models.IntegerField(default=50)
    requests_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Дійсний до")
    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default="1_month",
        verbose_name="Тарифний план",
    )

    @property
    def is_valid(self):
        return self.expires_at > timezone.now() and self.requests_used < self.requests_limit

    def __str__(self):
        return f"{self.user.username} - {self.key} ({self.get_plan_display()})"


class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Очікується'),
        ('approved', 'Оплачено'),
        ('declined', 'Відхилено'),
        ('error', 'Помилка'),
    ]

    PLAN_CHOICES = [
        ("1_month", "1 місяць"),
        ("3_months", "3 місяці"),
        ("1_year", "1 рік"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    api_key = models.ForeignKey(
        'APIKey', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Виданий API-ключ"
    )
    plan = models.CharField(
        max_length=20, choices=PLAN_CHOICES, default="1_month",
        verbose_name="Тарифний план"
    )
    order_reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='UAH')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Платіжна транзакція"
        verbose_name_plural = "Платіжні транзакції"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Transaction {self.order_reference} - {self.get_status_display()}"
