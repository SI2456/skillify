import random
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Session, Skill, UserProfile


TITLE_TEMPLATES = [
    "{skill} Fundamentals for Beginners",
    "Hands-On {skill} Workshop",
    "Advanced {skill} Techniques",
    "{skill} Crash Course",
    "Practical {skill} for Real-World Use",
    "{skill} Masterclass - Build Real Projects",
    "From Zero to Hero in {skill}",
    "{skill} Deep Dive: Tips and Tricks",
]

DESCRIPTION_TEMPLATES = [
    "Learn the core concepts of {skill} through hands-on examples and real-world practice.",
    "Interactive session with live demonstrations, Q&A, and personalized guidance.",
    "Build practical confidence in {skill} with focused exercises and tutor feedback.",
    "A beginner-friendly walkthrough of {skill} essentials with clear next steps.",
    "Level up your {skill} skills through real examples and guided practice.",
]

TIME_SLOTS = [
    (time(10, 0), time(11, 0)),
    (time(11, 30), time(12, 30)),
    (time(14, 0), time(15, 0)),
    (time(15, 30), time(16, 30)),
    (time(17, 0), time(18, 0)),
    (time(18, 30), time(19, 30)),
    (time(20, 0), time(21, 0)),
]

LEVELS = ["beginner", "intermediate", "advanced", "all"]
CREDIT_PRICES = [40, 45, 50, 55, 60, 65, 70, 75]


class Command(BaseCommand):
    help = "Seed idempotent future mock sessions for existing tutors."

    def add_arguments(self, parser):
        parser.add_argument(
            "--start-date",
            default="2026-05-09",
            help="First session date in YYYY-MM-DD format. Default: 2026-05-09",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days to seed. Default: 30",
        )
        parser.add_argument(
            "--slots-per-day",
            type=int,
            default=2,
            help="Number of sessions per tutor per day. Default: 2",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=5082026,
            help="Random seed for repeatable demo data. Default: 5082026",
        )

    def handle(self, *args, **options):
        try:
            start_date = datetime.strptime(options["start_date"], "%Y-%m-%d").date()
        except ValueError as exc:
            raise CommandError("--start-date must be in YYYY-MM-DD format") from exc

        days = options["days"]
        slots_per_day = options["slots_per_day"]
        if days < 1:
            raise CommandError("--days must be at least 1")
        if slots_per_day < 1 or slots_per_day > len(TIME_SLOTS):
            raise CommandError(f"--slots-per-day must be between 1 and {len(TIME_SLOTS)}")

        random.seed(options["seed"])

        tutor_profiles = (
            UserProfile.objects.filter(role="tutor")
            .select_related("user")
            .prefetch_related("skills")
            .order_by("user__id")
        )
        tutors = [profile.user for profile in tutor_profiles]
        skills = list(Skill.objects.all().order_by("id"))

        if not tutors:
            self.stdout.write(self.style.WARNING("No tutor users found. Future sessions were not seeded."))
            return
        if not skills:
            self.stdout.write(self.style.WARNING("No skills found. Future sessions were not seeded."))
            return

        created = 0
        skipped = 0
        end_date = start_date + timedelta(days=days - 1)

        with transaction.atomic():
            for day_offset in range(days):
                session_date = start_date + timedelta(days=day_offset)
                for tutor_index, tutor in enumerate(tutors):
                    tutor_skills = list(tutor.profile.skills.all()) or skills
                    day_slots = [
                        TIME_SLOTS[(day_offset + tutor_index + slot_offset * 3) % len(TIME_SLOTS)]
                        for slot_offset in range(slots_per_day)
                    ]

                    for slot_index, (start_time, end_time) in enumerate(day_slots):
                        if Session.objects.filter(
                            tutor=tutor,
                            date=session_date,
                            start_time=start_time,
                        ).exists():
                            skipped += 1
                            continue

                        skill = tutor_skills[(day_offset + tutor_index + slot_index) % len(tutor_skills)]
                        is_group = random.random() < 0.35
                        session_type = "group" if is_group else "one-to-one"

                        Session.objects.create(
                            tutor=tutor,
                            title=random.choice(TITLE_TEMPLATES).format(skill=skill.name),
                            description=random.choice(DESCRIPTION_TEMPLATES).format(skill=skill.name),
                            skill=skill,
                            level=random.choice(LEVELS),
                            date=session_date,
                            start_time=start_time,
                            end_time=end_time,
                            credits_required=random.choice(CREDIT_PRICES),
                            session_type=session_type,
                            max_participants=random.randint(4, 8) if is_group else 1,
                            status="upcoming",
                        )
                        created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created} future sessions from {start_date} to {end_date}. "
                f"Skipped {skipped} duplicates."
            )
        )
