from django.contrib.auth.models import Group, User

from rest_framework import serializers

from .models import Camera, Department, DetectedPlate, Employee, UserProfile, Vehicle


class CameraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Camera
        fields = ["id", "name", "stream_url", "location", "is_active"]


class EmployeeSerializer(serializers.ModelSerializer):
    has_details = serializers.SerializerMethodField()
    root_department = serializers.CharField(
        source="department.parent.name", default=None
    )
    specific_department = serializers.CharField(source="department.name", default=None)

    class Meta:
        model = Employee
        fields = "__all__"

    def get_has_details(self, obj):
        # Якщо у відділу є батько, значить це "специфічний відділ" і треба показувати деталі
        return obj.department and obj.department.parent is not None


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "parent"]


class VehicleSerializer(serializers.ModelSerializer):
    # Використовуємо безпечний метод замість ReadOnlyField
    owner_name = serializers.SerializerMethodField()
    created_by_username = serializers.SerializerMethodField()

    # Якщо фронтенду потрібні деталі про працівника (опціонально)
    employee_details = EmployeeSerializer(source="employee", read_only=True)

    class Meta:
        model = Vehicle
        fields = "__all__"

    # Ця функція безпечно формує ПІБ і ніколи не видасть помилку JSON
    def get_owner_name(self, obj):
        if obj.employee:
            # Якщо це авто працівника
            return f"{obj.employee.last_name} {obj.employee.first_name}"
        # Якщо це авто гостя
        return f"{obj.owner_last_name} {obj.owner_first_name}"

    def get_created_by_username(self, obj):
        if obj.created_by:
            return obj.created_by.username
        return None

    def validate_plate_text(self, value):
        return value.upper().strip()


class DetectedPlateSerializer(serializers.ModelSerializer):
    vehicle = VehicleSerializer(read_only=True)
    camera_name = serializers.CharField(source="camera.name", read_only=True)

    class Meta:
        model = DetectedPlate
        fields = [
            "id",
            "plate_text",
            "timestamp",
            "confidence",
            "vehicle",
            "camera_name",
        ]


class UserSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "password", "first_name", "last_name", "phone")

    def create(self, validated_data):
        phone = validated_data.pop("phone")
        password = validated_data.pop("password")

        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        UserProfile.objects.create(user=user, phone=phone)

        guest_group, created = Group.objects.get_or_create(name="Guests")
        user.groups.add(guest_group)

        return user
