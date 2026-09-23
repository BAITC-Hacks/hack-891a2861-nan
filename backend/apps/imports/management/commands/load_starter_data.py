from pathlib import Path

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.employees.models import Employee
from apps.imports.services import DatasetValidationError, import_dataset


class Command(BaseCommand):
    help = "Import the official Career Quest starter dataset and create demo login accounts"

    def add_arguments(self, parser):
        parser.add_argument("--path", default="/data/starter")
        parser.add_argument("--if-empty", action="store_true")

    def handle(self, *args, **options):
        path = Path(options["path"])
        required = {
            "employees_file": path / "employees.json",
            "skills_file": path / "skills.json",
            "events_file": path / "events.json",
            "history_file": path / "activity_history.csv",
        }
        missing = [str(file) for file in required.values() if not file.exists()]
        if missing:
            raise CommandError(f"Missing starter files: {', '.join(missing)}")

        should_import = not (options["if_empty"] and Employee.objects.count() >= 200)
        if should_import:
            try:
                handles = {name: file.open("rb") for name, file in required.items()}
                try:
                    counts = import_dataset(**handles)
                finally:
                    for handle in handles.values():
                        handle.close()
            except DatasetValidationError as exc:
                raise CommandError(str(exc.errors[:10])) from exc
            self.stdout.write(self.style.SUCCESS(f"Imported official dataset: {counts}"))
        else:
            self.stdout.write("Official employee dataset already exists; import skipped")

        hr, _ = User.objects.get_or_create(
            username="hr",
            defaults={"email": "hr@example.invalid", "role": User.Role.HR},
        )
        hr.role = User.Role.HR
        hr.set_password("hr-demo")
        hr.save()

        employee_password = make_password("employee-demo")
        for employee in Employee.objects.iterator():
            user, _ = User.objects.get_or_create(
                username=employee.employee_id.lower(),
                defaults={"role": User.Role.EMPLOYEE},
            )
            user.role = User.Role.EMPLOYEE
            user.password = employee_password
            user.save(update_fields=["role", "password"])
            if employee.user_id != user.id:
                employee.user = user
                employee.save(update_fields=["user"])
        self.stdout.write(self.style.SUCCESS("Created HR and employee demo accounts"))
