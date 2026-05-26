import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.utils import timezone
from recognition.models import UserProfile, Vehicle, AccessPermit, PaymentTransaction

class Command(BaseCommand):
    help = "Populate the database with highly realistic guest users, vehicles, and payment transactions"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting guest database population..."))

        # 1. Отримуємо або створюємо групу Guests
        guest_group, _ = Group.objects.get_or_create(name="Guests")

        # 2. Список реалістичних даних для генерації
        guests_data = [
            {
                "username": "demian_danylyuk",
                "first_name": "Дем'ян",
                "last_name": "Данилюк",
                "phone": "+380671234567",
                "email": "demian.danylyuk@gmail.com",
                "plate": "BC7777CX",
                "brand": "Tesla Model 3",
            },
            {
                "username": "olena_symchuk",
                "first_name": "Олена",
                "last_name": "Симчук",
                "phone": "+380509876543",
                "email": "o.symchuk@outlook.com",
                "plate": "KA5544BE",
                "brand": "Toyota RAV4",
            },
            {
                "username": "andriy_sheva",
                "first_name": "Андрій",
                "last_name": "Шевченко",
                "phone": "+380931112233",
                "email": "sheva.andriy@ukr.net",
                "plate": "AA9988HB",
                "brand": "Audi A6",
            },
            {
                "username": "svitlana_p",
                "first_name": "Світлана",
                "last_name": "Панченко",
                "phone": "+380974445566",
                "email": "s.panchenko@gmail.com",
                "plate": "AE1542HM",
                "brand": "Volkswagen Golf",
            },
            {
                "username": "dmytro_hrytsenko",
                "first_name": "Дмитро",
                "last_name": "Гриценко",
                "phone": "+380637778899",
                "email": "d.hrytsenko@yahoo.com",
                "plate": "BH9311BX",
                "brand": "BMW X5",
            },
            {
                "username": "tetyana_moroz",
                "first_name": "Тетяна",
                "last_name": "Мороз",
                "phone": "+380952223344",
                "email": "tanya.moroz@gmail.com",
                "plate": "AM0733CT",
                "brand": "Skoda Octavia",
            },
            {
                "username": "max_koval",
                "first_name": "Максим",
                "last_name": "Коваль",
                "phone": "+380675556677",
                "email": "m.koval@meta.ua",
                "plate": "AX4122KI",
                "brand": "Hyundai Tucson",
            },
            {
                "username": "yuliia_romanova",
                "first_name": "Юлія",
                "last_name": "Романова",
                "phone": "+380639990011",
                "email": "y.romanova@gmail.com",
                "plate": "AO3322CP",
                "brand": "Mazda CX-5",
            },
            {
                "username": "ihor_prots",
                "first_name": "Ігор",
                "last_name": "Проценко",
                "phone": "+380508887766",
                "email": "ihor.prots@gmail.com",
                "plate": "BC5050HP",
                "brand": "Mercedes-Benz C200",
            },
            {
                "username": "mariia_vasyl",
                "first_name": "Марія",
                "last_name": "Василенко",
                "phone": "+380973332211",
                "email": "m.vasylenko@i.ua",
                "plate": "AH7711EO",
                "brand": "Kia Sportage",
            }
        ]

        # 3. Видаляємо старі тестові записи гостей та авто, які не входять до нашого списку реалістичних акаунтів
        allowed_usernames = [item["username"] for item in guests_data]
        
        # Видаляємо старі гостьові авто, які не належать дозволеним реалістичним користувачам
        deleted_count, _ = Vehicle.objects.filter(employee__isnull=True).exclude(created_by__username__in=allowed_usernames).delete()
        if deleted_count:
            self.stdout.write(self.style.WARNING(f"Deleted {deleted_count} old/dummy guest vehicles."))

        # Видаляємо користувачів, які не є працівниками, адмінами чи операторами і не входять до нашого дозволеного списку гостей
        dummy_users = User.objects.filter(groups__name="Guests").exclude(username__in=allowed_usernames)
        if dummy_users.exists():
            self.stdout.write(self.style.WARNING(f"Deleting {dummy_users.count()} old dummy guest accounts (like 'myk')..."))
            dummy_users.delete()

        # 4. Створюємо реалістичні записи
        created_users_count = 0
        created_vehicles_count = 0

        for idx, item in enumerate(guests_data):
            # Перевіряємо чи юзер вже є, якщо немає — створюємо
            user, created = User.objects.get_or_create(
                username=item["username"],
                defaults={
                    "first_name": item["first_name"],
                    "last_name": item["last_name"],
                    "email": item["email"],
                    "is_active": True,
                }
            )

            if created:
                user.set_password("GatePlate2026!")
                user.save()
                user.groups.add(guest_group)
                created_users_count += 1
                
                # Створюємо профіль
                UserProfile.objects.get_or_create(
                    user=user,
                    defaults={"phone": item["phone"]}
                )

            # Видаляємо авто з таким номером, якщо воно раптом уже є, для уникнення колізій unique
            Vehicle.objects.filter(plate_text=item["plate"]).delete()

            # Створюємо гостьовий транспортний засіб
            vehicle = Vehicle.objects.create(
                employee=None,
                created_by=user,
                plate_text=item["plate"],
                brand_model=item["brand"],
                owner_first_name=item["first_name"],
                owner_last_name=item["last_name"]
            )
            created_vehicles_count += 1

            # Додаємо дозвіл на проїзд
            AccessPermit.objects.get_or_create(
                vehicle=vehicle,
                defaults={
                    "is_allowed": True,
                    "end_date": timezone.now().date() + timedelta(days=random.randint(15, 120))
                }
            )

            # Створюємо реалістичну оплачену транзакцію в історії для цього гостя через WayForPay
            order_ref = f"GP_GUEST_{user.id}_{item['plate']}_{int(timezone.now().timestamp()) - random.randint(100, 100000)}"
            PaymentTransaction.objects.create(
                user=user,
                transaction_type="guest_pass",
                plate_text=item["plate"],
                plan="",
                order_reference=order_ref,
                amount=50.00,
                currency="UAH",
                status="approved",
                created_at=timezone.now() - timedelta(hours=random.randint(1, 48))
            )

        self.stdout.write(self.style.SUCCESS(
            f"Successfully populated database!\n"
            f"  - Created/verified {created_users_count} realistic Guest Users\n"
            f"  - Registered {created_vehicles_count} Guest Vehicles with permits and transactions"
        ))
