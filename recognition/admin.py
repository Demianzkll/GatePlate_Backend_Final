from django.contrib import admin

from .models import Camera, Department, DetectedPlate, Employee, Vehicle

# Register your models here.

# Проста реєстрація
admin.site.register(Employee)
admin.site.register(Vehicle)
admin.site.register(DetectedPlate)
admin.site.register(Camera)
admin.site.register(Department)
