from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import (
    AnalysisStartView,
    DepartmentListView,
    DetectedPlateListView,
    EmployeeDetailView,
    EmployeeListCreateView,
    GuestVehicleCreateView,
    GuestVehicleListView,
    IssueAPIKeyView,
    LiveUpdateView,
    PaymentStatusAPIView,
    PhotoRecognitionAPIView,
    PlateConfirmView,
    VehicleViewSet,
    WayForPayWebhookAPIView,
    WayForPayCreatePaymentAPIView,
)

router = DefaultRouter()
router.register(r"vehicles", VehicleViewSet)

urlpatterns = [
    path("detected-plates/", DetectedPlateListView.as_view(), name="plates-api"),
    path("start-analysis/", AnalysisStartView.as_view(), name="start-analysis"),
    path("live-update/", LiveUpdateView.as_view(), name="live-update"),
    path("confirm-plate/", PlateConfirmView.as_view(), name="confirm-plate"),
    path("employees/", EmployeeListCreateView.as_view(), name="employees-list"),
    path("employees/<int:pk>/", EmployeeDetailView.as_view(), name="employee-detail"),
    path("departments/", DepartmentListView.as_view(), name="department-list"),
    path(
        "guest/register/",
        GuestVehicleCreateView.as_view(),
        name="guest-vehicle-register",
    ),
    path("recognize-photo/", PhotoRecognitionAPIView.as_view(), name="recognize-photo"),
    path("issue-api-key/", IssueAPIKeyView.as_view(), name="issue-api-key"),
    path("guests/", GuestVehicleListView.as_view(), name="guest-list"),
    path("payment/create/", WayForPayCreatePaymentAPIView.as_view(), name="wayforpay-create"),
    path("payment/webhook/", WayForPayWebhookAPIView.as_view(), name="wayforpay-webhook"),
    path("payment/status/", PaymentStatusAPIView.as_view(), name="payment-status"),
    path("", include(router.urls)),
]
