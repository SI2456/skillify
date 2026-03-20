import os
import random
from io import BytesIO
from datetime import date, time, timedelta

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from django.conf import settings
from core.models import Skill, UserProfile, Session, Booking, Review, Wallet, Transaction


def generate_profile_picture(name, color_hex):
    """
    Generate a simple profile picture with initials using Pillow.
    Falls back gracefully if Pillow is not installed.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        size = 300
        img = Image.new('RGB', (size, size), f'#{color_hex}')
        draw = ImageDraw.Draw(img)

        # Get initials (first letter of first and last name)
        parts = name.split()
        initials = parts[0][0].upper()
        if len(parts) > 1:
            initials += parts[-1][0].upper()

        # Try to use a nice font, fallback to default
        font_size = 120
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except (IOError, OSError):
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size)
            except (IOError, OSError):
                font = ImageFont.load_default()

        # Center the text
        bbox = draw.textbbox((0, 0), initials, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) / 2
        y = (size - text_height) / 2 - 10

        # Draw a subtle circle background
        circle_margin = 20
        draw.ellipse(
            [circle_margin, circle_margin, size - circle_margin, size - circle_margin],
            fill=f'#{color_hex}',
            outline='#ffffff',
            width=4
        )

        # Draw white initials
        draw.text((x, y), initials, fill='#ffffff', font=font)

        # Add a subtle gradient overlay for depth
        for i in range(size):
            alpha = int(30 * (i / size))
            draw.line([(0, i), (size, i)], fill=(0, 0, 0, alpha) if img.mode == 'RGBA' else None)

        buffer = BytesIO()
        img.save(buffer, format='PNG', quality=95)
        buffer.seek(0)
        return buffer.getvalue()

    except ImportError:
        return None


class Command(BaseCommand):
    help = 'Seed database with sample data including profile pictures and demo videos'

    def handle(self, *args, **kwargs):
        self.stdout.write('🌱 Seeding data...\n')

        # ==================== SKILLS ====================
        skill_data = [
            ('Dance', 'bi-music-note-beamed'),
            ('Python', 'bi-code-slash'),
            ('Guitar', 'bi-music-note'),
            ('Photography', 'bi-camera'),
            ('Public Speaking', 'bi-mic'),
            ('UI Design', 'bi-palette'),
            ('Data Science', 'bi-graph-up'),
            ('Singing', 'bi-soundwave'),
            ('Video Editing', 'bi-film'),
            ('Marketing', 'bi-megaphone'),
        ]
        skills = []
        for name, icon in skill_data:
            skill, _ = Skill.objects.get_or_create(name=name, defaults={'icon': icon})
            skills.append(skill)
        self.stdout.write(f'  ✅ Created {len(skills)} skills')

        # ==================== TUTORS ====================
        tutor_data = [
            {
                'username': 'tutor1@skillify.com',
                'first': 'Alex', 'last': 'Carter',
                'bio': 'Full Stack Developer with 5+ years of experience building web applications. I specialize in React, Node.js, and Django. My teaching approach focuses on hands-on projects and real-world problem solving. I believe the best way to learn coding is by doing it!',
                'expertise': 'Full Stack Developer | React & Django',
                'skills_idx': [1, 5, 6],
                'color': '667eea',
                'demo_video': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            },
            {
                'username': 'tutor2@skillify.com',
                'first': 'Sarah', 'last': 'Lee',
                'bio': 'UX/UI Designer passionate about creating beautiful, user-friendly interfaces. With 7 years in the industry, I have worked with startups and Fortune 500 companies. I teach design thinking, Figma, and prototyping.',
                'expertise': 'UX/UI Designer | Figma Expert',
                'skills_idx': [5, 3],
                'color': 'f093fb',
                'demo_video': 'https://www.youtube.com/watch?v=c9Wg6Cb_YlU',
            },
            {
                'username': 'tutor3@skillify.com',
                'first': 'Michael', 'last': 'Wong',
                'bio': 'Data Scientist with expertise in machine learning, statistical analysis, and Python. Previously worked at Google and Microsoft. I make complex data concepts simple and fun to learn.',
                'expertise': 'Data Scientist | ML Engineer',
                'skills_idx': [1, 6],
                'color': '4ECDC4',
                'demo_video': 'https://www.youtube.com/watch?v=ua-CiDNNj30',
            },
            {
                'username': 'tutor4@skillify.com',
                'first': 'Priya', 'last': 'Sharma',
                'bio': 'Communication coach and TEDx speaker helping professionals build confidence in public speaking. I have coached 500+ professionals across industries. My sessions are interactive and full of practical exercises.',
                'expertise': 'Communication Coach | TEDx Speaker',
                'skills_idx': [4, 9],
                'color': 'FFB84D',
                'demo_video': 'https://www.youtube.com/watch?v=HAnw168huqA',
            },
            {
                'username': 'tutor5@skillify.com',
                'first': 'James', 'last': 'Wilson',
                'bio': 'Professional guitarist with 10+ years of teaching experience. I play blues, rock, and classical styles. Whether you are a beginner or intermediate player, I can help you level up your skills and music theory.',
                'expertise': 'Guitar Instructor | Blues & Rock',
                'skills_idx': [2, 7],
                'color': 'f5576c',
                'demo_video': 'https://www.youtube.com/watch?v=OBmlCZTF4Xs',
            },
            {
                'username': 'tutor6@skillify.com',
                'first': 'Emily', 'last': 'Chen',
                'bio': 'Professional photographer specializing in portrait and landscape photography. Published in National Geographic and Vogue. I teach composition, lighting, and post-processing techniques.',
                'expertise': 'Photographer | Lightroom Pro',
                'skills_idx': [3, 8],
                'color': '764ba2',
                'demo_video': 'https://www.youtube.com/watch?v=V1fnMrEGPc8',
            },
            {
                'username': 'tutor7@skillify.com',
                'first': 'David', 'last': 'Brown',
                'bio': 'Digital marketing expert with 8+ years of experience in SEO, content marketing, social media strategy, and paid advertising. I help students understand how to grow brands online.',
                'expertise': 'Digital Marketing Expert | SEO & Ads',
                'skills_idx': [9, 5],
                'color': '43b581',
                'demo_video': 'https://www.youtube.com/watch?v=bixR-KIJKYM',
            },
            {
                'username': 'tutor8@skillify.com',
                'first': 'Lisa', 'last': 'Park',
                'bio': 'Professional dancer and choreographer specializing in contemporary, hip-hop, and Latin dance styles. Former member of a touring dance company. I make learning dance fun and accessible for everyone!',
                'expertise': 'Dance Instructor | Choreographer',
                'skills_idx': [0, 7],
                'color': 'e91e63',
                'demo_video': 'https://www.youtube.com/watch?v=M4fasWpog5Q',
            },
            {
                'username': 'tutor9@skillify.com',
                'first': 'Raj', 'last': 'Patel',
                'bio': 'Video editor with expertise in Adobe Premiere Pro, After Effects, and DaVinci Resolve. I have edited content for YouTubers with 1M+ subscribers. I teach practical editing workflows and techniques.',
                'expertise': 'Video Editor | Premiere & After Effects',
                'skills_idx': [8, 3],
                'color': 'ff6b35',
                'demo_video': 'https://www.youtube.com/watch?v=O6ERELse_QY',
            },
            {
                'username': 'tutor10@skillify.com',
                'first': 'Anna', 'last': 'Kim',
                'bio': 'Vocal coach and professional singer with a background in classical and pop music. Trained at Berklee College of Music. I help students discover and develop their unique voice through personalized exercises.',
                'expertise': 'Vocal Coach | Berklee Trained',
                'skills_idx': [7, 0],
                'color': '00bcd4',
                'demo_video': 'https://www.youtube.com/watch?v=3tmd-ClpJxA',
            },
        ]

        tutors = []
        pics_generated = 0
        for td in tutor_data:
            user, created = User.objects.get_or_create(
                username=td['username'],
                defaults={
                    'email': td['username'],
                    'first_name': td['first'],
                    'last_name': td['last'],
                    'is_active': True,
                }
            )
            if created:
                user.set_password('123456')
                user.save()

            profile = user.profile
            profile.role = 'tutor'
            profile.bio = td['bio']
            profile.expertise = td['expertise']
            profile.is_verified = True
            profile.trust_score = round(random.uniform(70, 98), 1)
            profile.demo_video = td['demo_video']
            profile.linkedin = f'https://linkedin.com/in/{td["first"].lower()}{td["last"].lower()}'
            profile.github = f'https://github.com/{td["first"].lower()}{td["last"].lower()}'

            # Experience & Education seed data
            exp_data = [
                (8, 'B.Tech Computer Science, IIT Delhi (2016)\nM.S. Machine Learning, Stanford University (2018)'),
                (5, 'B.Sc. Mathematics, University of Mumbai (2019)\nPG Diploma in Data Science, IIIT Hyderabad (2020)'),
                (12, 'B.E. Software Engineering, BITS Pilani (2012)\nMBA, IIM Ahmedabad (2014)'),
                (3, 'B.Tech IT, NIT Trichy (2021)\nGoogle Certified Professional Cloud Architect'),
                (7, 'B.Sc. Physics, Delhi University (2017)\nM.Tech AI & Robotics, IISc Bangalore (2019)'),
                (10, 'Bachelor of Design, NID Ahmedabad (2014)\nMFA Interaction Design, SVA New York (2016)'),
                (6, 'B.Com, Shri Ram College of Commerce (2018)\nCFA Level 3 Candidate\nCA (Chartered Accountant)'),
                (4, 'B.Tech ECE, VIT Vellore (2020)\nAWS Solutions Architect Certified'),
                (15, 'B.Sc. Computer Science, BHU (2009)\nPh.D. Natural Language Processing, JNU (2014)'),
                (9, 'B.Tech Mechanical, IIT Bombay (2015)\nM.S. Robotics, Carnegie Mellon University (2017)'),
            ]
            idx = tutor_data.index(td) % len(exp_data)
            profile.experience_years = exp_data[idx][0]
            profile.education = exp_data[idx][1]
            profile.show_experience = True
            profile.show_education = True

            # Generate and save profile picture
            full_name = f'{td["first"]} {td["last"]}'
            pic_data = generate_profile_picture(full_name, td['color'])
            if pic_data:
                filename = f'{td["first"].lower()}_{td["last"].lower()}.png'
                profile.profile_picture.save(filename, ContentFile(pic_data), save=False)
                pics_generated += 1

            profile.save()

            for idx in td['skills_idx']:
                profile.skills.add(skills[idx])

            # Set wallet balance
            wallet = user.wallet
            wallet.balance = random.randint(80, 500)
            wallet.save()

            tutors.append(user)

        self.stdout.write(f'  ✅ Created {len(tutors)} tutor users')
        self.stdout.write(f'  📸 Generated {pics_generated} profile pictures')
        self.stdout.write(f'  🎬 Added {len([t for t in tutor_data if t["demo_video"]])} demo videos')

        # ==================== SESSIONS ====================
        today = date.today()
        session_templates = [
            {'title': 'Python Programming Fundamentals', 'skill': 'Python', 'credits': 50, 'desc': 'Learn Python from scratch — variables, loops, functions, and your first real project.'},
            {'title': 'Advanced React Development', 'skill': 'Python', 'credits': 60, 'desc': 'Deep dive into React hooks, context API, custom hooks, and performance optimization.'},
            {'title': 'UI/UX Design Workshop', 'skill': 'UI Design', 'credits': 55, 'desc': 'Hands-on Figma workshop covering wireframing, prototyping, and design systems.'},
            {'title': 'Data Science with Pandas', 'skill': 'Data Science', 'credits': 70, 'desc': 'Master data manipulation, cleaning, and visualization with Pandas and Matplotlib.'},
            {'title': 'Public Speaking Masterclass', 'skill': 'Public Speaking', 'credits': 45, 'desc': 'Overcome stage fright and learn to deliver powerful, memorable presentations.'},
            {'title': 'Guitar for Beginners', 'skill': 'Guitar', 'credits': 40, 'desc': 'Learn basic chords, strumming patterns, and play your first 3 songs.'},
            {'title': 'Photography Basics', 'skill': 'Photography', 'credits': 50, 'desc': 'Understand composition, lighting, and camera settings for stunning photos.'},
            {'title': 'Digital Marketing Strategy', 'skill': 'Marketing', 'credits': 55, 'desc': 'Build a complete digital marketing plan — SEO, content, social media, and ads.'},
            {'title': 'Dance Fundamentals', 'skill': 'Dance', 'credits': 40, 'desc': 'Learn basic footwork, rhythm, and body movement for contemporary dance.'},
            {'title': 'Video Editing with Premiere Pro', 'skill': 'Video Editing', 'credits': 65, 'desc': 'Professional editing workflow — cuts, transitions, color grading, and export settings.'},
            {'title': 'Vocal Training Session', 'skill': 'Singing', 'credits': 45, 'desc': 'Warm-up exercises, breathing techniques, and range expansion for singers.'},
            {'title': 'Machine Learning Basics', 'skill': 'Data Science', 'credits': 75, 'desc': 'Intro to supervised learning — linear regression, decision trees, and model evaluation.'},
        ]

        sessions_created = 0

        # Preply-style: multiple 30min/1hr slots per day for each tutor
        evening_slots = [
            (time(15, 30), time(16, 30)),
            (time(16, 0), time(17, 0)),
            (time(16, 30), time(17, 30)),
            (time(17, 0), time(18, 0)),
            (time(19, 0), time(20, 0)),
            (time(19, 30), time(20, 30)),
            (time(20, 0), time(21, 0)),
            (time(20, 30), time(21, 30)),
            (time(21, 0), time(22, 0)),
            (time(21, 30), time(22, 30)),
        ]

        for i, st in enumerate(session_templates):
            tutor = tutors[i % len(tutors)]
            skill = Skill.objects.get(name=st['skill'])

            # Create slots for next 7 days
            for day_offset in range(7):
                session_date = today + timedelta(days=day_offset)

                # 3-6 random slots per day
                num_slots = random.randint(3, 6)
                day_slots = random.sample(evening_slots, min(num_slots, len(evening_slots)))

                for start, end in day_slots:
                    Session.objects.get_or_create(
                        title=st['title'],
                        tutor=tutor,
                        date=session_date,
                        start_time=start,
                        defaults={
                            'description': st['desc'],
                            'skill': skill,
                            'end_time': end,
                            'credits_required': st['credits'],
                            'session_type': 'one-to-one',
                            'level': random.choice(['beginner', 'intermediate', 'advanced', 'all']),
                            'max_participants': 1,
                            'status': 'upcoming',
                        }
                    )
                    sessions_created += 1

        # Create completed sessions with reviews
        review_comments = [
            'Great session! {tutor} explained everything clearly and was very patient.',
            'Excellent teaching style. I learned so much about {skill} in just one hour!',
            'Highly recommended! {tutor} is very knowledgeable and makes complex topics simple.',
            'One of the best sessions I have had. The hands-on approach was really helpful.',
            'Very professional and well-prepared. Will definitely book again!',
            'Amazing experience! {tutor} went above and beyond to help me understand {skill}.',
            '{tutor} has a fantastic way of breaking down {skill} concepts. Loved it!',
            'Really enjoyed this session. Practical, engaging, and informative.',
        ]

        for i in range(5):
            tutor = tutors[i]
            skill = skills[tutor_data[i]['skills_idx'][0]]
            completed_session, created = Session.objects.get_or_create(
                title=f"Completed: {skill.name} Basics",
                tutor=tutor,
                defaults={
                    'description': f"Past session on {skill.name} fundamentals.",
                    'skill': skill,
                    'date': today - timedelta(days=random.randint(1, 30)),
                    'start_time': time(14, 0),
                    'end_time': time(15, 0),
                    'credits_required': 50,
                    'status': 'completed',
                }
            )
            if created:
                sessions_created += 1
                # Create reviews from multiple reviewers
                num_reviews = random.randint(1, 3)
                for j in range(num_reviews):
                    reviewer = tutors[(i + 5 + j) % len(tutors)]
                    if reviewer != tutor:
                        comment_template = random.choice(review_comments)
                        comment = comment_template.format(
                            tutor=tutor.first_name,
                            skill=skill.name
                        )
                        Review.objects.get_or_create(
                            session=completed_session,
                            reviewer=reviewer,
                            defaults={
                                'tutor': tutor,
                                'rating': random.choice([4, 4, 5, 5, 5]),
                                'comment': comment,
                            }
                        )

                        # Create booking for reviewer
                        Booking.objects.get_or_create(
                            learner=reviewer,
                            session=completed_session,
                            defaults={
                                'status': 'completed',
                                'credits_paid': 50,
                            }
                        )

        # Recalculate trust scores based on actual reviews
        for tutor in tutors:
            reviews = Review.objects.filter(tutor=tutor)
            if reviews.exists():
                from django.db.models import Avg
                avg = reviews.aggregate(avg=Avg('rating'))['avg']
                review_count = reviews.count()
                completed = Session.objects.filter(tutor=tutor, status='completed').count()
                rating_score = min((avg / 5) * 60, 60)
                session_score = min(completed * 2, 25)
                rev_score = min(review_count * 1.5, 15)
                tutor.profile.trust_score = round(min(rating_score + session_score + rev_score, 100), 1)
                tutor.profile.save()

        self.stdout.write(f'  ✅ Created {sessions_created} sessions (upcoming + completed)')

        # ==================== LEARNER ====================
        learner, created = User.objects.get_or_create(
            username='learner@skillify.com',
            defaults={
                'email': 'learner@skillify.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'is_active': True,
            }
        )
        if created:
            learner.set_password('123456')
            learner.save()
            profile = learner.profile
            profile.role = 'learner'
            profile.bio = 'Enthusiastic learner looking to pick up new skills!'
            profile.is_verified = True
            profile.save()

            # Generate profile picture for learner too
            pic_data = generate_profile_picture('John Doe', '4facfe')
            if pic_data:
                profile.profile_picture.save('john_doe.png', ContentFile(pic_data), save=True)

            wallet = learner.wallet
            wallet.balance = 250
            wallet.save()
            Transaction.objects.create(
                wallet=wallet,
                transaction_type='signup_bonus',
                amount=100,
                description='Welcome bonus credits',
                balance_after=250,
            )
        self.stdout.write('  ✅ Created learner account')

        # ==================== ADMIN ====================
        if not User.objects.filter(is_superuser=True).exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@skillify.com',
                password='admin123',
                first_name='Admin',
                last_name='User',
            )
            admin_user.profile.is_verified = True
            admin_user.profile.save()
        self.stdout.write('  ✅ Created admin superuser')

        # ==================== SUMMARY ====================
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('🎉 Seed data created successfully!'))
        self.stdout.write('')
        self.stdout.write('📋 Test Accounts:')
        self.stdout.write('  ┌───────────────────────────────────────────────────┐')
        self.stdout.write('  │  Learner: learner@skillify.com / 123456           │')
        self.stdout.write('  │  Tutors:  tutor1@skillify.com to tutor10 / 123456 │')
        self.stdout.write('  │  Admin:   admin / admin123                        │')
        self.stdout.write('  └───────────────────────────────────────────────────┘')
        self.stdout.write('')
        self.stdout.write('📸 Profile Pictures: Generated for all 10 tutors + 1 learner')
        self.stdout.write('🎬 Demo Videos: YouTube links added for all 10 tutors')
        self.stdout.write('   (Videos embed directly on tutor profile pages)')
        self.stdout.write('')
        self.stdout.write('💡 Try: Login as learner → Browse Skills → Click a tutor → See their video!')
