import random
from datetime import datetime, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Avg

from core.models import Booking, Review, Session, Skill, Transaction, UserProfile, Wallet


REVIEWERS = [
    ("learner1@skillify.com", "Maya", "Singh"),
    ("learner2@skillify.com", "Arjun", "Mehta"),
    ("learner3@skillify.com", "Nisha", "Rao"),
    ("learner4@skillify.com", "Kabir", "Khan"),
    ("learner5@skillify.com", "Ananya", "Iyer"),
    ("learner6@skillify.com", "Rohan", "Verma"),
    ("learner7@skillify.com", "Ishita", "Das"),
    ("learner8@skillify.com", "Vikram", "Nair"),
]

COMMENTS = [
    "{tutor} explained {skill} clearly and made the session easy to follow.",
    "Great class. The examples were practical, and I felt more confident with {skill}.",
    "{tutor} was patient, prepared, and answered every question in detail.",
    "Very useful session with strong real-world guidance. I would book again.",
    "The pace was perfect, and the feedback helped me understand my mistakes.",
    "Excellent teaching style. Complex {skill} ideas felt simple by the end.",
    "A friendly, focused session with lots of actionable tips.",
    "{tutor} gave clear next steps and useful practice ideas after the class.",
]


class Command(BaseCommand):
    help = "Seed mock completed sessions and reviews for all tutor profiles."

    def add_arguments(self, parser):
        parser.add_argument(
            "--end-date",
            default="2026-05-08",
            help="Latest completed session date in YYYY-MM-DD format. Default: 2026-05-08",
        )
        parser.add_argument(
            "--sessions-per-tutor",
            type=int,
            default=3,
            help="Completed sessions to ensure per tutor. Default: 3",
        )
        parser.add_argument(
            "--reviews-per-session",
            type=int,
            default=2,
            help="Reviews to ensure per completed session. Default: 2",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=9052026,
            help="Random seed for repeatable demo reviews. Default: 9052026",
        )

    def handle(self, *args, **options):
        try:
            end_date = datetime.strptime(options["end_date"], "%Y-%m-%d").date()
        except ValueError as exc:
            raise CommandError("--end-date must be in YYYY-MM-DD format") from exc

        sessions_per_tutor = options["sessions_per_tutor"]
        reviews_per_session = options["reviews_per_session"]
        if sessions_per_tutor < 1:
            raise CommandError("--sessions-per-tutor must be at least 1")
        if reviews_per_session < 1:
            raise CommandError("--reviews-per-session must be at least 1")

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
            self.stdout.write(self.style.WARNING("No tutor users found. Mock reviews were not seeded."))
            return
        if not skills:
            self.stdout.write(self.style.WARNING("No skills found. Mock reviews were not seeded."))
            return

        created_sessions = 0
        created_bookings = 0
        created_reviews = 0
        reviewers = []

        with transaction.atomic():
            for email, first_name, last_name in REVIEWERS:
                reviewer, created = User.objects.get_or_create(
                    username=email,
                    defaults={
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "is_active": True,
                    },
                )
                if created:
                    reviewer.set_password("123456")
                    reviewer.save()

                profile, _ = UserProfile.objects.get_or_create(user=reviewer)
                profile.role = "learner"
                profile.is_verified = True
                profile.save()
                Wallet.objects.get_or_create(user=reviewer, defaults={"balance": 250})
                reviewers.append(reviewer)

            for tutor_index, tutor in enumerate(tutors):
                tutor_skills = list(tutor.profile.skills.all()) or skills

                for session_index in range(sessions_per_tutor):
                    skill = tutor_skills[(tutor_index + session_index) % len(tutor_skills)]
                    session_date = end_date - timedelta(days=(tutor_index + session_index) % 8)
                    session, created = Session.objects.get_or_create(
                        tutor=tutor,
                        title=f"Completed: {skill.name} Practice Session {session_index + 1}",
                        date=session_date,
                        start_time=time(14 + (session_index % 4), 0),
                        defaults={
                            "description": f"Past hands-on session covering {skill.name} fundamentals and guided practice.",
                            "skill": skill,
                            "end_time": time(15 + (session_index % 4), 0),
                            "credits_required": random.choice([40, 45, 50, 55, 60]),
                            "session_type": "one-to-one",
                            "level": random.choice(["beginner", "intermediate", "advanced", "all"]),
                            "max_participants": 1,
                            "status": "completed",
                        },
                    )
                    if created:
                        created_sessions += 1
                    session.status = "completed"
                    session.save(update_fields=["status"])

                    session_reviewers = [
                        reviewers[(tutor_index + session_index + offset) % len(reviewers)]
                        for offset in range(reviews_per_session)
                    ]
                    for reviewer in session_reviewers:
                        booking, booking_created = Booking.objects.get_or_create(
                            learner=reviewer,
                            session=session,
                            defaults={
                                "status": "completed",
                                "credits_paid": session.credits_required,
                                "tutor_confirmed": True,
                                "learner_confirmed": True,
                            },
                        )
                        if booking_created:
                            created_bookings += 1
                            wallet = reviewer.wallet
                            Transaction.objects.get_or_create(
                                wallet=wallet,
                                transaction_type="booking_payment",
                                amount=session.credits_required,
                                description=f"Booking: {session.title}",
                                balance_after=wallet.balance,
                            )

                        comment = random.choice(COMMENTS).format(
                            tutor=tutor.first_name or tutor.username,
                            skill=session.skill.name,
                        )
                        _, review_created = Review.objects.get_or_create(
                            session=session,
                            reviewer=reviewer,
                            defaults={
                                "tutor": tutor,
                                "rating": random.choice([4, 4, 5, 5, 5]),
                                "comment": comment,
                            },
                        )
                        if review_created:
                            created_reviews += 1

                reviews = Review.objects.filter(tutor=tutor)
                if reviews.exists():
                    avg = reviews.aggregate(avg=Avg("rating"))["avg"] or 0
                    completed_count = Session.objects.filter(tutor=tutor, status="completed").count()
                    review_count = reviews.count()
                    rating_score = min((avg / 5) * 60, 60)
                    session_score = min(completed_count * 2, 25)
                    review_score = min(review_count * 1.5, 15)
                    tutor.profile.trust_score = round(min(rating_score + session_score + review_score, 100), 1)
                    tutor.profile.save(update_fields=["trust_score"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_reviews} reviews, {created_sessions} completed sessions, "
                f"and {created_bookings} bookings for {len(tutors)} tutors."
            )
        )
