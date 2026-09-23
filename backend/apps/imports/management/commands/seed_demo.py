from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.activities.models import ActivityHistory
from apps.catalog.models import Event, EventSkillGain, Grade, GradeRequirement, Role, Skill
from apps.employees.models import Employee, EmployeeSkill
from apps.recommendations.models import RecommendationSnapshot


class Command(BaseCommand):
    help = "Load a deterministic synthetic Career Quest demo dataset"

    def add_arguments(self, parser):
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="Do nothing when employee data already exists",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@example.invalid", "role": User.Role.ADMIN},
        )
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password("careerquest-demo")
        admin.save()
        if options["if_empty"] and Employee.objects.exists():
            self.stdout.write("Employee data already exists; demo seed skipped")
            return
        RecommendationSnapshot.objects.all().delete()
        ActivityHistory.objects.all().delete()
        Employee.objects.all().delete()
        Event.objects.all().delete()
        GradeRequirement.objects.all().delete()
        Grade.objects.all().delete()
        Role.objects.all().delete()
        Skill.objects.all().delete()

        role = Role.objects.create(
            code="backend_engineer",
            name_en="Backend Engineer",
            name_ru="Backend-разработчик",
            name_kk="Backend әзірлеуші",
        )
        grades = {}
        for rank, (code, en, ru, kk) in enumerate(
            [
                ("junior", "Junior", "Junior", "Junior"),
                ("middle", "Middle", "Middle", "Middle"),
                ("senior", "Senior", "Senior", "Senior"),
                ("lead", "Lead", "Lead", "Lead"),
            ],
            start=1,
        ):
            grades[code] = Grade.objects.create(
                role=role, code=code, rank=rank, name_en=en, name_ru=ru, name_kk=kk
            )

        skills_data = [
            ("SK_PYTHON", "Python", "Python", "Python", "hard"),
            ("SK_SYSTEM_DESIGN", "System Design", "Системный дизайн", "Жүйелік дизайн", "hard"),
            ("SK_DATABASES", "Databases", "Базы данных", "Дерекқорлар", "hard"),
            (
                "SK_CLOUD",
                "Cloud Architecture",
                "Облачная архитектура",
                "Бұлттық архитектура",
                "hard",
            ),
            (
                "SK_PUBLIC_SPEAKING",
                "Public Speaking",
                "Публичные выступления",
                "Көпшілік алдында сөйлеу",
                "soft",
            ),
            ("SK_MENTORING", "Mentoring", "Менторство", "Тәлімгерлік", "soft"),
        ]
        skills = {
            code: Skill.objects.create(code=code, name_en=en, name_ru=ru, name_kk=kk, kind=kind)
            for code, en, ru, kk, kind in skills_data
        }
        requirements = {
            "middle": {"SK_PYTHON": (3, 4), "SK_DATABASES": (3, 3), "SK_SYSTEM_DESIGN": (2, 3)},
            "senior": {
                "SK_PYTHON": (4, 4),
                "SK_DATABASES": (4, 4),
                "SK_SYSTEM_DESIGN": (4, 5),
                "SK_CLOUD": (3, 4),
                "SK_PUBLIC_SPEAKING": (3, 2),
            },
            "lead": {
                "SK_SYSTEM_DESIGN": (5, 5),
                "SK_CLOUD": (4, 4),
                "SK_PUBLIC_SPEAKING": (4, 4),
                "SK_MENTORING": (4, 5),
            },
        }
        for grade_code, items in requirements.items():
            for skill_code, (level, priority) in items.items():
                GradeRequirement.objects.create(
                    grade=grades[grade_code],
                    skill=skills[skill_code],
                    required_level=level,
                    priority=priority,
                )

        events_data = [
            (
                "EV_SYSTEM_DESIGN",
                "System Design Lab",
                "Лаборатория System Design",
                "Hands-on architecture workshop with a senior reviewer",
                "Практикум по архитектуре с senior-ревьюером",
                "workshop",
                8,
                [("SK_SYSTEM_DESIGN", 1, 5)],
            ),
            (
                "EV_ARCH_PROJECT",
                "Architecture Challenge",
                "Архитектурный челлендж",
                "Design a resilient service and defend the trade-offs",
                "Спроектируйте отказоустойчивый сервис и защитите решения",
                "project",
                16,
                [("SK_SYSTEM_DESIGN", 1, 4), ("SK_CLOUD", 1, 4)],
            ),
            (
                "EV_DB_ADVANCED",
                "Advanced PostgreSQL",
                "Продвинутый PostgreSQL",
                "Query planning, indexing and production diagnostics",
                "Планы запросов, индексы и production-диагностика",
                "course",
                10,
                [("SK_DATABASES", 1, 5)],
            ),
            (
                "EV_CLOUD_FOUNDATIONS",
                "Cloud Architecture Foundations",
                "Основы облачной архитектуры",
                "Build secure and observable cloud systems",
                "Построение безопасных и наблюдаемых облачных систем",
                "course",
                12,
                [("SK_CLOUD", 1, 4)],
            ),
            (
                "EV_SPEAKING",
                "Technical Storytelling",
                "Технический сторителлинг",
                "Present complex technical ideas clearly",
                "Научитесь понятно представлять сложные технические идеи",
                "workshop",
                4,
                [("SK_PUBLIC_SPEAKING", 1, 5)],
            ),
            (
                "EV_MENTOR",
                "Mentoring Practice",
                "Практика менторства",
                "A guided four-week mentoring engagement",
                "Четырёхнедельная практика менторства",
                "mentoring",
                8,
                [("SK_MENTORING", 1, 5), ("SK_PUBLIC_SPEAKING", 1, 4)],
            ),
        ]
        events = {}
        for code, en, ru, desc_en, desc_ru, fmt, hours, gains in events_data:
            event = Event.objects.create(
                code=code,
                name_en=en,
                name_ru=ru,
                name_kk=en,
                description_en=desc_en,
                description_ru=desc_ru,
                description_kk=desc_en,
                event_type="development",
                format=fmt,
                duration_hours=hours,
            )
            event.audience_roles.add(role)
            events[code] = event
            for skill_code, gain, maximum in gains:
                EventSkillGain.objects.create(
                    event=event, skill=skills[skill_code], gain=gain, max_level=maximum
                )

        employees_data = [
            (
                "E0028",
                "Alex Morgan",
                "middle",
                52,
                {
                    "SK_PYTHON": 3,
                    "SK_SYSTEM_DESIGN": 2,
                    "SK_DATABASES": 3,
                    "SK_CLOUD": 2,
                    "SK_PUBLIC_SPEAKING": 1,
                    "SK_MENTORING": 1,
                },
            ),
            (
                "E0041",
                "Dana Lee",
                "middle",
                38,
                {
                    "SK_PYTHON": 4,
                    "SK_SYSTEM_DESIGN": 3,
                    "SK_DATABASES": 4,
                    "SK_CLOUD": 2,
                    "SK_PUBLIC_SPEAKING": 3,
                    "SK_MENTORING": 2,
                },
            ),
            (
                "E0063",
                "Sam Taylor",
                "junior",
                18,
                {
                    "SK_PYTHON": 2,
                    "SK_SYSTEM_DESIGN": 1,
                    "SK_DATABASES": 2,
                    "SK_CLOUD": 1,
                    "SK_PUBLIC_SPEAKING": 2,
                    "SK_MENTORING": 1,
                },
            ),
            (
                "E0087",
                "Robin Chen",
                "senior",
                61,
                {
                    "SK_PYTHON": 5,
                    "SK_SYSTEM_DESIGN": 4,
                    "SK_DATABASES": 4,
                    "SK_CLOUD": 3,
                    "SK_PUBLIC_SPEAKING": 3,
                    "SK_MENTORING": 2,
                },
            ),
            (
                "E0102",
                "Jordan Kim",
                "middle",
                29,
                {
                    "SK_PYTHON": 4,
                    "SK_SYSTEM_DESIGN": 4,
                    "SK_DATABASES": 3,
                    "SK_CLOUD": 3,
                    "SK_PUBLIC_SPEAKING": 2,
                    "SK_MENTORING": 1,
                },
            ),
        ]
        employees = {}
        for employee_id, name, grade_code, tenure, levels in employees_data:
            employee = Employee.objects.create(
                employee_id=employee_id,
                display_name=name,
                role=role,
                grade=grades[grade_code],
                tenure_months=tenure,
                organisation_unit="Digital Channels",
                locale="ru",
            )
            employees[employee_id] = employee
            EmployeeSkill.objects.bulk_create(
                [
                    EmployeeSkill(employee=employee, skill=skills[code], level=level)
                    for code, level in levels.items()
                ]
            )

        now = timezone.now()
        histories = [
            ("E0028", "EV_SPEAKING", "no_show", 120, False),
            ("E0028", "EV_SPEAKING", "declined", 80, None),
            ("E0028", "EV_SPEAKING", "no_show", 35, False),
            ("E0028", "EV_DB_ADVANCED", "completed", 170, True),
            ("E0028", "EV_CLOUD_FOUNDATIONS", "completed", 90, True),
            ("E0041", "EV_DB_ADVANCED", "completed", 100, True),
            ("E0041", "EV_SYSTEM_DESIGN", "completed", 60, True),
            ("E0063", "EV_SPEAKING", "completed", 40, True),
            ("E0087", "EV_ARCH_PROJECT", "completed", 75, True),
            ("E0087", "EV_MENTOR", "no_show", 25, False),
            ("E0102", "EV_SYSTEM_DESIGN", "completed", 110, True),
        ]
        for employee_id, event_code, status, days, on_time in histories:
            ActivityHistory.objects.create(
                employee=employees[employee_id],
                event=events[event_code],
                status=status,
                occurred_at=now - timedelta(days=days),
                completed_on_time=on_time,
                source="demo",
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(employees)} employees, {len(events)} events and {len(skills)} skills"
            )
        )
