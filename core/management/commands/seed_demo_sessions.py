import random
from datetime import timedelta, time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Session, Skill, UserProfile


TITLE_TEMPLATES = [
    "{skill} Fundamentals for Beginners",
    "{skill} Masterclass — Build Real Projects",
    "Advanced {skill} Techniques",
    "{skill} Crash Course",
    "Hands-On {skill} Workshop",
    "From Zero to Hero in {skill}",
    "{skill} Deep Dive: Tips & Tricks",
    "Practical {skill} for Real-World Use",
]

DESCRIPTION_TEMPLATES = [
    "Learn the core concepts of {skill} through hands-on examples and real-world projects. Perfect for anyone starting their journey.",
    "Deep dive into {skill} with practical exercises, code reviews, and one-on-one guidance. Build production-ready skills.",
    "Interactive session covering advanced {skill} topics. Includes live coding, Q&A, and project feedback.",
    "A beginner-friendly walkthrough of {skill} essentials. No prior experience needed — just curiosity and a laptop.",
    "Level up your {skill} game with focused drills, live demonstrations, and personalized feedback from an experienced tutor.",
    "Comprehensive {skill} workshop with real examples. Walk away with a mini-project you can add to your portfolio.",
]

TIME_SLOTS = [
    (time(10, 0), time(11, 0)),
    (time(14, 0), time(15, 0)),
    (time(16, 0), time(17, 0)),
    (time(18, 0), time(19, 0)),
    (time(19, 30), time(20, 30)),
]

LEVELS = ['beginner', 'intermediate', 'advanced', 'all']
CREDIT_PRICES = [10, 15, 25, 40, 50]


class Command(BaseCommand):
    help = 'Seed future-dated demo sessions for Browse Skills page'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', type=int, default=2,
            help='Number of sessions per tutor (default: 2)',
        )
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all past sessions (date < today) before seeding',
        )

    def handle(self, *args, **options):
        count = options['count']
        clear = options['clear']
        today = timezone.now().date()

        # --- Clear past sessions ---
        if clear:
            past = Session.objects.filter(date__lt=today)
            deleted_count = past.count()
            past.delete()
            self.stdout.write(self.style.WARNING(
                f"Deleted {deleted_count} past sessions."
            ))

        # --- Find tutors ---
        tutor_profiles = UserProfile.objects.filter(role='tutor').select_related('user')
        if not tutor_profiles.exists():
            self.stdout.write(self.style.ERROR(
                "No tutors found! Create tutor accounts first."
            ))
            return

        tutors = [tp.user for tp in tutor_profiles]
        self.stdout.write(f"Found {len(tutors)} tutor(s).")

        # --- Find skills ---
        skills = list(Skill.objects.all())
        if not skills:
            self.stdout.write(self.style.ERROR(
                "No skills found! Run: python manage.py create_skills"
            ))
            return

        self.stdout.write(f"Found {len(skills)} skill(s).")

        # --- Seed sessions ---
        created_total = 0
        skipped_total = 0
        summary = []

        with transaction.atomic():
            for tutor in tutors:
                created_for_tutor = 0
                # Pick skills for this tutor (from their profile if available, else random)
                tutor_skills = list(tutor.profile.skills.all())
                if not tutor_skills:
                    tutor_skills = random.sample(skills, min(len(skills), count))

                for i in range(count):
                    skill = tutor_skills[i % len(tutor_skills)]
                    # Pick a future date (1-10 days out)
                    day_offset = random.randint(1, 10)
                    session_date = today + timedelta(days=day_offset)

                    start_time, end_time = random.choice(TIME_SLOTS)

                    # Check for duplicate (same tutor, date, start_time)
                    if Session.objects.filter(
                        tutor=tutor, date=session_date, start_time=start_time
                    ).exists():
                        skipped_total += 1
                        continue

                    level = random.choice(LEVELS)
                    is_group = random.random() > 0.4  # 60% group, 40% 1-on-1
                    session_type = 'group' if is_group else 'one-to-one'
                    max_participants = random.randint(5, 10) if is_group else 1

                    title = random.choice(TITLE_TEMPLATES).format(skill=skill.name)
                    description = random.choice(DESCRIPTION_TEMPLATES).format(skill=skill.name)
                    credits = random.choice(CREDIT_PRICES)

                    Session.objects.create(
                        tutor=tutor,
                        title=title,
                        description=description,
                        skill=skill,
                        level=level,
                        date=session_date,
                        start_time=start_time,
                        end_time=end_time,
                        credits_required=credits,
                        session_type=session_type,
                        max_participants=max_participants,
                        status='upcoming',
                    )
                    created_for_tutor += 1

                created_total += created_for_tutor
                summary.append((tutor.get_full_name() or tutor.email, created_for_tutor))

        # --- Print summary ---
        self.stdout.write("")
        self.stdout.write("=" * 45)
        self.stdout.write(self.style.SUCCESS(f"  Created {created_total} sessions total"))
        if skipped_total:
            self.stdout.write(self.style.WARNING(f"  Skipped {skipped_total} (duplicate date+time)"))
        self.stdout.write("=" * 45)
        for name, cnt in summary:
            self.stdout.write(f"  {name}: {cnt} sessions")
        self.stdout.write("=" * 45)
