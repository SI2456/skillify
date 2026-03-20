"""
Skillify Chatbot Engine — Learner-Focused Assistant
15 interaction types: greeting, course list, course details, recommendations,
tutor search, skill suggestions, learning roadmaps, enrollment help,
certificates, platform explanation, motivation, popular skills, help, goodbye, fallback.
"""

import re
import random
from django.db.models import Avg, Count, Q


# ===== 1. GREETINGS =====
GREETINGS = ['hi', 'hello', 'hey', 'hola', 'sup', 'yo', 'good morning', 'good afternoon',
             'good evening', 'namaste', 'howdy', 'whats up', "what's up", 'greetings']
GREETING_RESPONSES = [
    "Hey there! 👋 I'm Skilly, your learning assistant. What would you like to learn today?",
    "Hello! 😊 I can help you find courses, suggest skills, or plan your learning journey!",
    "Hi! 👋 Ready to learn something new? Ask me about any skill or course!",
    "Namaste! 🙏 What skill are you curious about today?",
]

# ===== 14. GOODBYE / THANKS =====
FAREWELLS = ['bye', 'goodbye', 'see you', 'quit', 'exit', 'later', 'cya']
FAREWELL_RESPONSES = [
    "Goodbye! 👋 Keep learning, keep growing! 🎓",
    "See you later! Remember — consistency beats intensity. 💪",
    "Bye! Your next skill breakthrough is just one session away! 😊",
]
THANKS = ['thank', 'thanks', 'thx', 'ty', 'appreciate', 'helpful', 'great help']
THANKS_RESPONSES = [
    "You're welcome! 😊 Happy to help. Ask me anything else!",
    "Glad I could help! 🎓 Let me know if you need more guidance.",
    "Anytime! Learning is a journey — I'm here whenever you need me. 💪",
]


# ===== 3. COURSE / SKILL DETAILS =====
SKILL_DETAILS = {
    'python': {
        'name': 'Python',
        'icon': '🐍',
        'description': 'High-level programming language known for simplicity and readability. Used for web development, data science, AI/ML, automation, and scripting.',
        'difficulty': 'Beginner-friendly',
        'time_to_learn': '2-4 weeks for basics, 3-6 months for proficiency',
        'prerequisites': 'None — great first language!',
        'what_you_learn': 'Variables, loops, functions, OOP, file handling, web frameworks (Django/Flask), data libraries (Pandas, NumPy)',
        'career': 'Web Developer (₹4-15L), Data Scientist (₹6-20L), ML Engineer (₹8-25L), Automation Engineer (₹4-12L)',
        'projects': 'Calculator, To-do app, Web scraper, Blog with Django, Weather app, Chatbot, REST API',
        'resources': 'Python.org tutorial, Automate the Boring Stuff, W3Schools, HackerRank, Kaggle',
        'roadmap': [
            ('Week 1-2', 'Basics: variables, data types, if/else, loops'),
            ('Week 3-4', 'Functions, modules, lists, dictionaries, file I/O'),
            ('Month 2', 'OOP: classes, inheritance, polymorphism'),
            ('Month 3', 'Choose a path: Web (Django) or Data (Pandas)'),
            ('Month 4-6', 'Build 3-5 projects for your portfolio'),
        ],
    },
    'guitar': {
        'name': 'Guitar',
        'icon': '🎸',
        'description': 'Stringed instrument with 6 strings. Types: Acoustic (hollow body) and Electric (needs amp). Great for solo playing, bands, and songwriting.',
        'difficulty': 'Moderate — finger pain is real at first!',
        'time_to_learn': '1-3 months for basic songs, 6-12 months for intermediate',
        'prerequisites': 'A guitar! Acoustic recommended for beginners (₹3,000-8,000)',
        'what_you_learn': 'Chords (open & barre), strumming patterns, fingerpicking, music theory basics, song playing',
        'career': 'Session Musician, Music Teacher, Band Performer, YouTube Musician, Worship Leader',
        'projects': 'Learn 10 songs, Write an original song, Record a cover, Perform for friends/family',
        'resources': 'JustinGuitar.com (free), Fender Play, YouTube (Marty Music), Ultimate Guitar (tabs)',
        'roadmap': [
            ('Week 1-2', 'Hold guitar, tune it, learn Em, Am, C chords'),
            ('Week 3-4', 'G, D chords, basic down strumming, first song'),
            ('Month 2', 'Chord transitions, up-down strumming, 3-5 songs'),
            ('Month 3-4', 'Barre chords (F, Bm), fingerpicking intro'),
            ('Month 5-6', 'Play 10+ songs confidently, basic music theory'),
        ],
    },
    'photography': {
        'name': 'Photography',
        'icon': '📷',
        'description': 'Art of capturing light to create images. Includes portrait, landscape, street, product, wedding, wildlife, and food photography.',
        'difficulty': 'Easy to start, lifetime to master',
        'time_to_learn': '1-2 months for fundamentals, 6+ months to develop style',
        'prerequisites': 'Any camera (smartphone works!)',
        'what_you_learn': 'Exposure triangle (aperture, shutter, ISO), composition rules, lighting, editing (Lightroom)',
        'career': 'Wedding Photographer (₹20K-2L/event), Product Photography (₹3-10L), Freelance, Stock Photography',
        'projects': '365-day photo challenge, Portrait series, Street photography walk, Edit 50 photos',
        'resources': 'YouTube (Peter McKinnon, Mango Street), Lightroom tutorials, r/photography',
        'roadmap': [
            ('Week 1', 'Understand exposure triangle, shoot in Auto+Manual'),
            ('Week 2-3', 'Composition: rule of thirds, leading lines, framing'),
            ('Month 2', 'Lighting: golden hour, shadows, flash basics'),
            ('Month 3', 'Editing: Lightroom workflow, color correction'),
            ('Month 4-6', 'Develop your style, build a portfolio'),
        ],
    },
    'dance': {
        'name': 'Dance',
        'icon': '💃',
        'description': 'Art of movement and expression through rhythm. Styles: Bollywood, Hip Hop, Contemporary, Classical (Bharatanatyam, Kathak), Salsa, Ballet.',
        'difficulty': 'Varies by style — Bollywood is beginner-friendly!',
        'time_to_learn': '1-2 months for basic moves, 6+ months for a full routine',
        'prerequisites': 'Comfortable clothes and space to move!',
        'what_you_learn': 'Rhythm, coordination, body isolation, choreography, flexibility, stage presence',
        'career': 'Dance Teacher, Choreographer, Performer, Fitness Instructor, YouTube Creator',
        'projects': 'Learn a full choreography, Record a dance video, Perform at an event',
        'resources': 'YouTube (Matt Steffanina, Deepak Tulsyan), STEEZY Studio, Local dance classes',
        'roadmap': [
            ('Week 1-2', 'Basic rhythm, body isolation, simple steps'),
            ('Week 3-4', 'Learn a simple choreography (Bollywood/Hip Hop)'),
            ('Month 2', 'Improve coordination, learn 2-3 routines'),
            ('Month 3-4', 'Freestyle basics, musicality, performance quality'),
            ('Month 5-6', 'Create your own choreography, record videos'),
        ],
    },
    'public speaking': {
        'name': 'Public Speaking',
        'icon': '🎤',
        'description': 'Art of presenting ideas to an audience. Essential for meetings, pitches, interviews, conferences, and leadership.',
        'difficulty': 'Challenging mentally, but very learnable',
        'time_to_learn': '1-2 months to feel comfortable, 6+ months to excel',
        'prerequisites': 'Just courage! And an audience (even a mirror works)',
        'what_you_learn': 'Structure, storytelling, body language, voice modulation, handling Q&A, overcoming stage fear',
        'career': 'Corporate Trainer (₹5-15L), Motivational Speaker, TEDx Speaker, Sales Leader, Consultant',
        'projects': 'Give a 5-min speech, Join Toastmasters, Present at work/college, Record yourself',
        'resources': 'Toastmasters International, TED Talks, YouTube (Vinh Giang), "Talk Like TED" book',
        'roadmap': [
            ('Week 1-2', 'Structure: opening hook, 3 points, strong close'),
            ('Week 3-4', 'Practice: record yourself, reduce filler words'),
            ('Month 2', 'Body language, eye contact, voice modulation'),
            ('Month 3', 'Handle Q&A, impromptu speaking, storytelling'),
            ('Month 4-6', 'Present to bigger audiences, get feedback, iterate'),
        ],
    },
    'ui design': {
        'name': 'UI Design',
        'icon': '🎨',
        'description': 'Designing visual elements of apps and websites — buttons, colors, typography, layouts. UI = how it looks, UX = how it feels.',
        'difficulty': 'Beginner-friendly with tools like Figma',
        'time_to_learn': '1-2 months for basics, 4-6 months for professional work',
        'prerequisites': 'None — Figma is free and browser-based!',
        'what_you_learn': 'Design principles, color theory, typography, wireframing, prototyping, responsive design',
        'career': 'UI Designer (₹4-15L), UX Designer (₹5-18L), Product Designer (₹8-25L), Freelance (₹500-5000/project)',
        'projects': 'Redesign a popular app, Design a landing page, Create a design system, Portfolio on Behance',
        'resources': 'Figma (free), Dribbble, Behance, YouTube (DesignCourse), Google UX cert on Coursera',
        'roadmap': [
            ('Week 1-2', 'Design principles: contrast, alignment, proximity'),
            ('Week 3-4', 'Figma basics: frames, components, auto-layout'),
            ('Month 2', 'Color theory, typography, icon design'),
            ('Month 3', 'Wireframing, prototyping, user flows'),
            ('Month 4-6', 'Build 3-5 portfolio projects, responsive design'),
        ],
    },
    'data science': {
        'name': 'Data Science',
        'icon': '📊',
        'description': 'Extracting insights from data using statistics, programming, and domain expertise. Includes ML, Deep Learning, NLP, Computer Vision.',
        'difficulty': 'Moderate — needs math + coding',
        'time_to_learn': '3-6 months for basics, 6-12 months to be job-ready',
        'prerequisites': 'Basic Python, high school math (stats helps)',
        'what_you_learn': 'Python (pandas, numpy), statistics, SQL, data visualization, machine learning, deep learning',
        'career': 'Data Analyst (₹4-10L), Data Scientist (₹8-25L), ML Engineer (₹10-30L), Data Engineer (₹6-20L)',
        'projects': 'Titanic survival prediction, Movie recommender, Sales dashboard, Sentiment analysis',
        'resources': 'Kaggle, Google Data Analytics cert, Andrew Ng ML course, StatQuest YouTube',
        'roadmap': [
            ('Week 1-2', 'Python basics: pandas, numpy, matplotlib'),
            ('Week 3-4', 'Statistics: mean, median, probability, distributions'),
            ('Month 2', 'SQL, data cleaning, exploratory data analysis'),
            ('Month 3-4', 'Machine Learning: regression, classification, clustering'),
            ('Month 5-6', 'Build 3-5 projects, Kaggle competitions, portfolio'),
        ],
    },
    'singing': {
        'name': 'Singing',
        'icon': '🎵',
        'description': 'Producing musical sounds with your voice — pitch control, breath support, tone quality, and emotional expression.',
        'difficulty': 'Anyone can learn! Natural talent helps but practice matters more',
        'time_to_learn': '1-3 months for basics, 6+ months for confidence',
        'prerequisites': 'Your voice! A tuner app helps (free)',
        'what_you_learn': 'Breathing technique, pitch matching, vocal range, warm-ups, performance, ear training',
        'career': 'Professional Singer, Music Teacher, Session Vocalist, YouTube Artist, Worship Leader',
        'projects': 'Record a cover song, Perform at an open mic, Write original lyrics, Vocal exercise routine',
        'resources': 'YouTube (Cheryl Porter, Jacobs Vocal Academy), Smule/Starmaker apps, Local music schools',
        'roadmap': [
            ('Week 1-2', 'Breathing exercises, posture, basic warm-ups'),
            ('Week 3-4', 'Pitch matching, singing simple melodies'),
            ('Month 2', 'Learn 3-5 songs in your range, recording practice'),
            ('Month 3-4', 'Expand vocal range, dynamics, emotional delivery'),
            ('Month 5-6', 'Performance skills, mic technique, stage presence'),
        ],
    },
    'video editing': {
        'name': 'Video Editing',
        'icon': '🎬',
        'description': 'Assembling and manipulating video footage to create polished content. Used for YouTube, films, ads, reels, corporate videos.',
        'difficulty': 'Easy to start with modern tools',
        'time_to_learn': '2-4 weeks for basics, 2-3 months for professional work',
        'prerequisites': 'A computer and free software (DaVinci Resolve)',
        'what_you_learn': 'Cutting, transitions, text/titles, color grading, audio mixing, effects, export settings',
        'career': 'YouTube Editor (₹15K-80K/month), Freelance (₹500-5000/video), Film Editor (₹4-15L), Motion Graphics (₹5-18L)',
        'projects': 'Edit a vlog, Create a montage, YouTube intro, Before/after reel, Short film',
        'resources': 'YouTube (Justin Odisho, Casey Faris), DaVinci Resolve (free), Skillshare tutorials',
        'roadmap': [
            ('Week 1', 'Install software, learn interface, basic cuts'),
            ('Week 2-3', 'Transitions, text, music, audio sync'),
            ('Month 2', 'Color grading, effects, speed ramps'),
            ('Month 3', 'Advanced: keyframes, masking, motion graphics'),
            ('Month 4+', 'Build reel of 5-10 edited projects'),
        ],
    },
    'marketing': {
        'name': 'Marketing',
        'icon': '📣',
        'description': 'Promoting and selling products/services. Digital Marketing includes SEO, Social Media, Content, Email, PPC Ads, Influencer Marketing.',
        'difficulty': 'Easy concepts, execution takes practice',
        'time_to_learn': '1-2 months for basics, 3-6 months for real results',
        'prerequisites': 'None — start with a social media account!',
        'what_you_learn': 'SEO, social media strategy, content creation, email marketing, analytics, paid ads',
        'career': 'Digital Marketing Manager (₹5-15L), SEO Specialist (₹3-10L), Social Media Manager (₹3-12L), Freelance (₹20K-1L/month)',
        'projects': 'Grow a social media page, Write SEO blog posts, Run a small ad campaign, Email newsletter',
        'resources': 'Google Digital Garage (free cert), HubSpot Academy, Meta Blueprint, Neil Patel blog',
        'roadmap': [
            ('Week 1-2', 'Marketing fundamentals, target audience, value proposition'),
            ('Week 3-4', 'Content creation, social media basics, SEO intro'),
            ('Month 2', 'Email marketing, Google Analytics, keyword research'),
            ('Month 3-4', 'Paid ads (Google, Meta), A/B testing, copywriting'),
            ('Month 5-6', 'Build case studies, get certifications, freelance'),
        ],
    },
}

# ===== 4. COURSE RECOMMENDATIONS BY INTEREST =====
RECOMMENDATIONS = {
    'coding': ['Python', 'UI Design', 'Data Science'],
    'programming': ['Python', 'Data Science'],
    'tech': ['Python', 'Data Science', 'UI Design', 'Video Editing'],
    'creative': ['Photography', 'UI Design', 'Video Editing', 'Dance', 'Singing'],
    'music': ['Guitar', 'Singing'],
    'art': ['Photography', 'UI Design', 'Dance'],
    'business': ['Marketing', 'Public Speaking', 'Data Science'],
    'career': ['Python', 'Data Science', 'Marketing', 'Public Speaking'],
    'communication': ['Public Speaking', 'Marketing'],
    'fitness': ['Dance'],
    'fun': ['Guitar', 'Dance', 'Singing', 'Photography'],
    'freelance': ['UI Design', 'Video Editing', 'Photography', 'Marketing'],
    'money': ['Python', 'Data Science', 'Marketing', 'Video Editing'],
    'high paying': ['Data Science', 'Python', 'UI Design'],
    'easy': ['Photography', 'Marketing', 'Guitar'],
    'hard': ['Data Science', 'Public Speaking'],
    'fast': ['Video Editing', 'Photography', 'Marketing'],
}

# ===== 11. MOTIVATION =====
MOTIVATIONS = [
    "💪 **Remember:** Every expert was once a beginner. Keep going!",
    "🔥 **\"The best time to plant a tree was 20 years ago. The second best time is now.\"** — Chinese Proverb",
    "🎯 **Tip:** Just 30 minutes of daily practice beats 5 hours once a week. Consistency wins!",
    "⭐ **You've got this!** The fact that you're here means you're already ahead of most people.",
    "🚀 **Progress, not perfection.** Celebrate small wins — they add up to big results!",
    "📚 **Learning tip:** Teach what you learn to someone else. It's the fastest way to master a topic.",
    "💡 **Stuck?** Take a 10-minute break, then come back. Your brain processes info during rest!",
    "🌟 **\"The only way to do great work is to love what you do.\"** — Steve Jobs",
    "🎓 **Fun fact:** It takes roughly 20 hours of focused practice to get reasonably good at a new skill. That's just 40 mins/day for a month!",
    "🏆 **Don't compare your Chapter 1 to someone else's Chapter 20.** Focus on YOUR progress.",
]


def get_chatbot_response(user_message, user=None):
    """Main chatbot handler — routes to 15 interaction types."""
    from .models import Skill, UserProfile, Session, Booking, Review

    msg = user_message.lower().strip()
    msg_clean = re.sub(r'[^\w\s]', '', msg)

    if not msg:
        return _response("Please type something! Ask about a skill, course, or say **help**.", ['Help', 'Popular skills', 'Motivate me'])

    # ===== 1. GREETINGS =====
    if any(g == msg_clean or msg_clean.startswith(g + ' ') for g in GREETINGS):
        resp = random.choice(GREETING_RESPONSES)
        if user:
            resp = resp.replace("Hey there!", f"Hey {user.first_name}!").replace("Hello!", f"Hello {user.first_name}!")
        return _response(resp, ['Popular skills', 'Recommend me a skill', 'Help'])

    # ===== 14. GOODBYE / THANKS =====
    if any(f in msg_clean for f in FAREWELLS):
        return _response(random.choice(FAREWELL_RESPONSES), [])
    if any(t in msg_clean for t in THANKS):
        return _response(random.choice(THANKS_RESPONSES), ['Popular skills', 'Recommend me a skill'])

    # ===== 11. MOTIVATION =====
    if any(w in msg for w in ['motivate', 'motivation', 'inspire', 'feeling lazy', 'not motivated',
                               'give up', 'too hard', 'i cant', "i can't", 'discouraged',
                               'inspire me', 'motivate me', 'feeling down', 'stuck',
                               'frustrated', 'not improving', 'no progress']):
        return _response(random.choice(MOTIVATIONS), ['Learning tips', 'Popular skills', 'Find a tutor'])

    # ===== 2. COURSE LIST =====
    if any(w in msg for w in ['what courses', 'course list', 'all courses', 'available courses',
                               'what can i learn', 'what skills', 'all skills', 'skill list',
                               'list of courses', 'what do you offer', 'what do you teach',
                               'show courses', 'show skills', 'available skills']):
        return _get_course_list()

    # ===== 12. POPULAR SKILLS =====
    if any(w in msg for w in ['popular', 'trending', 'most popular', 'top skills',
                               'best skills', 'most booked', 'hot skills', 'in demand']):
        return _get_popular_skills()

    # ===== 4. RECOMMENDATIONS =====
    if any(w in msg for w in ['recommend', 'suggest', 'what should i learn', 'suggestion',
                               'which skill', 'which course', 'confused', 'help me choose',
                               'best for me', 'what to learn', 'dont know what to learn',
                               "don't know what", 'suggest me', 'recommend me',
                               'good for beginner', 'where to start', 'start learning']):
        return _get_recommendation(msg)

    # ===== 7. LEARNING ROADMAP =====
    if any(w in msg for w in ['roadmap', 'learning path', 'learning plan', 'study plan',
                               'how to start', 'where to begin', 'step by step',
                               'how long to learn', 'how many months', 'how many weeks',
                               'time to learn', 'duration', 'syllabus', 'curriculum']):
        return _get_roadmap(msg)

    # ===== 3. COURSE DETAILS (skill-specific questions) =====
    for skill_key, skill in SKILL_DETAILS.items():
        if skill_key in msg or skill['name'].lower() in msg:
            return _get_skill_answer(skill_key, skill, msg)

    # ===== 5. TUTOR SEARCH =====
    if any(w in msg for w in ['find tutor', 'search tutor', 'tutor for', 'who teaches',
                               'need tutor', 'want tutor', 'book tutor', 'best tutor',
                               'top tutor', 'top rated', 'highest rated']):
        return _find_tutors(msg)

    # ===== 6. SKILL SUGGESTIONS (by category) =====
    if any(w in msg for w in ['coding skill', 'creative skill', 'music skill', 'tech skill',
                               'business skill', 'easy skill', 'fun skill', 'high paying skill',
                               'freelance skill']):
        return _get_recommendation(msg)

    # ===== 8. ENROLLMENT HELP =====
    if any(w in msg for w in ['how to book', 'how to enroll', 'enroll', 'join course', 'register for',
                               'sign up for', 'book session', 'booking', 'how to join',
                               'how to start session', 'payment', 'credits', 'wallet',
                               'how much', 'cost', 'price', 'free']):
        return _get_enrollment_help(msg)

    # ===== 9. CERTIFICATES =====
    if any(w in msg for w in ['certificate', 'certification', 'credential', 'proof',
                               'completion certificate', 'do i get certificate', 'verified']):
        return _response(
            "📜 **Certificates:**\n\nSkillify currently doesn't issue certificates, but here's how to prove your skills:\n\n• **Reviews on your profile** — show your learning journey\n• **Portfolio projects** — best proof of skill\n• **External certificates:** Many skills have free certs:\n  - Python → HackerRank, Google\n  - Data Science → Kaggle, Google\n  - Marketing → Google Digital Garage, HubSpot\n  - UI Design → Google UX cert on Coursera\n\n**Tip:** Employers value portfolios > certificates!",
            ['Popular skills', 'Recommend me a skill']
        )

    # ===== 10. PLATFORM EXPLANATION =====
    if any(w in msg for w in ['what is skillify', 'about skillify', 'how does it work',
                               'explain platform', 'about this', 'what is this',
                               'how to use', 'features', 'what can you do']):
        return _get_platform_info(msg)

    # ===== LIVE DATA: My balance =====
    if any(w in msg for w in ['my balance', 'my credits', 'my wallet', 'check balance']):
        if user:
            return _response(f"💰 Your balance: **{user.wallet.balance} credits**.\n\n[Check Wallet](/wallet/)", ['How to book', 'Popular skills'])
        return _response("Please [login](/login/) to check your balance.", ['Login', 'Register'])

    # ===== LIVE DATA: My sessions =====
    if any(w in msg for w in ['my session', 'my booking', 'upcoming session', 'my class']):
        if user:
            upcoming = Booking.objects.filter(learner=user, status__in=['confirmed', 'tutor_completed']).count()
            completed = Booking.objects.filter(learner=user, status__in=['completed', 'pending_review']).count()
            return _response(f"📚 You have **{upcoming}** upcoming and **{completed}** completed sessions.\n\n[My Sessions](/my-sessions/)", ['How to book', 'Popular skills'])
        return _response("Please [login](/login/) to see sessions.", ['Login'])

    # ===== LIVE DATA: Platform stats =====
    if any(w in msg for w in ['how many tutor', 'how many user', 'how many session',
                               'statistics', 'platform stats', 'total']):
        return _get_platform_stats()

    # ===== 13. HELP =====
    if any(w in msg_clean for w in ['help', 'menu', 'commands', 'options', 'what can you do']):
        return _get_help()

    # ===== 15. FALLBACK =====
    return _response(
        f"🤔 I'm not sure about \"{user_message}\", but I can help with:\n\n"
        "• **\"What is Python?\"** — learn about any skill\n"
        "• **\"Recommend me a skill\"** — get personalized suggestions\n"
        "• **\"Guitar roadmap\"** — step-by-step learning plan\n"
        "• **\"Find a tutor\"** — search available tutors\n"
        "• **\"Popular skills\"** — see trending courses\n"
        "• **\"Motivate me\"** — get inspired!\n\n"
        "Type **help** for everything I can do!",
        ['Help', 'Popular skills', 'Recommend me a skill', 'Motivate me']
    )


# ===== HELPER: Build response dict =====
def _response(message, suggestions):
    return {'message': message, 'suggestions': suggestions}


# ===== 2. COURSE LIST =====
def _get_course_list():
    from .models import Skill, Session
    skills = Skill.objects.annotate(
        session_count=Count('sessions', filter=Q(sessions__status='upcoming'))
    ).order_by('-session_count')

    if not skills.exists():
        return _response("No courses available yet. Check back soon!", ['Help'])

    msg = "📚 **Available Courses on Skillify:**\n\n"
    for s in skills:
        detail = SKILL_DETAILS.get(s.name.lower(), {})
        icon = detail.get('icon', '📘')
        difficulty = detail.get('difficulty', '')
        msg += f"{icon} **{s.name}** — {s.session_count} upcoming sessions"
        if difficulty:
            msg += f" · _{difficulty}_"
        msg += "\n"

    msg += "\n💡 Ask me about any skill for details, roadmap, or career info!"
    return _response(msg, ['Recommend me a skill', 'Popular skills', 'Python details'])


# ===== 12. POPULAR SKILLS =====
def _get_popular_skills():
    from .models import Skill, Booking
    popular = Skill.objects.annotate(
        booking_count=Count('sessions__bookings')
    ).order_by('-booking_count')[:5]

    msg = "🔥 **Most Popular Skills on Skillify:**\n\n"
    for i, s in enumerate(popular, 1):
        detail = SKILL_DETAILS.get(s.name.lower(), {})
        icon = detail.get('icon', '📘')
        msg += f"{i}. {icon} **{s.name}** — {s.booking_count} bookings\n"

    msg += "\n📈 These are based on actual bookings on the platform!"
    return _response(msg, ['Recommend me a skill', 'Course list', 'Find a tutor'])


# ===== 3. COURSE DETAILS =====
def _get_skill_answer(skill_key, skill, msg):
    """Answer specific questions about a skill."""

    # Career / salary / jobs
    if any(w in msg for w in ['career', 'salary', 'job', 'earn', 'money', 'pay', 'scope',
                               'future', 'placement', 'package']):
        return _response(
            f"{skill['icon']} **{skill['name']} — Career & Salary:**\n\n{skill['career']}\n\n**Projects to build:** {skill['projects']}",
            [f"{skill['name']} roadmap", f"Find {skill['name']} tutor", 'Other careers']
        )

    # Roadmap / how to learn
    if any(w in msg for w in ['roadmap', 'how to learn', 'how to start', 'where to start',
                               'step by step', 'plan', 'path', 'begin', 'getting started']):
        return _format_roadmap(skill)

    # Prerequisites / requirements
    if any(w in msg for w in ['prerequisite', 'requirement', 'need to know', 'before learning',
                               'what do i need', 'preparation']):
        return _response(
            f"{skill['icon']} **{skill['name']} — Prerequisites:**\n\n{skill['prerequisites']}\n\n**Difficulty:** {skill['difficulty']}\n**Time to learn:** {skill['time_to_learn']}",
            [f"{skill['name']} roadmap", f"Find {skill['name']} tutor"]
        )

    # Resources
    if any(w in msg for w in ['resource', 'book', 'youtube', 'tutorial', 'where to learn',
                               'free resource', 'study material', 'course', 'online']):
        return _response(
            f"{skill['icon']} **{skill['name']} — Learning Resources:**\n\n{skill['resources']}\n\n**On Skillify:** Book a 1-on-1 session with an expert tutor for personalized guidance!",
            [f"Find {skill['name']} tutor", f"{skill['name']} roadmap"]
        )

    # Difficulty / hard / easy
    if any(w in msg for w in ['difficult', 'hard', 'easy', 'tough', 'challenge', 'how long',
                               'time', 'duration', 'weeks', 'months']):
        return _response(
            f"{skill['icon']} **{skill['name']} — Difficulty & Time:**\n\n**Difficulty:** {skill['difficulty']}\n**Time to learn:** {skill['time_to_learn']}\n**Prerequisites:** {skill['prerequisites']}",
            [f"{skill['name']} roadmap", 'Motivate me']
        )

    # Projects
    if any(w in msg for w in ['project', 'practice', 'build', 'hands on', 'portfolio']):
        return _response(
            f"{skill['icon']} **{skill['name']} — Project Ideas:**\n\n{skill['projects']}\n\n💡 **Tip:** Building projects is the best way to learn and impress employers!",
            [f"{skill['name']} roadmap", f"Find {skill['name']} tutor"]
        )

    # Default: full overview
    return _response(
        f"{skill['icon']} **{skill['name']}**\n\n{skill['description']}\n\n"
        f"**Difficulty:** {skill['difficulty']}\n"
        f"**Time to learn:** {skill['time_to_learn']}\n"
        f"**Prerequisites:** {skill['prerequisites']}\n"
        f"**You'll learn:** {skill['what_you_learn']}\n\n"
        f"Want the roadmap, career info, or a tutor?",
        [f"{skill['name']} roadmap", f"{skill['name']} career", f"Find {skill['name']} tutor"]
    )


# ===== 7. ROADMAP =====
def _get_roadmap(msg):
    """Find which skill the roadmap is for."""
    for skill_key, skill in SKILL_DETAILS.items():
        if skill_key in msg or skill['name'].lower() in msg:
            return _format_roadmap(skill)

    # No skill specified
    skill_names = ', '.join([s['name'] for s in SKILL_DETAILS.values()])
    return _response(
        f"📋 I can create a roadmap for: **{skill_names}**\n\nTry: \"Python roadmap\" or \"Guitar learning path\"",
        [f"{list(SKILL_DETAILS.values())[0]['name']} roadmap", f"{list(SKILL_DETAILS.values())[1]['name']} roadmap"]
    )


def _format_roadmap(skill):
    """Format a skill's roadmap nicely."""
    msg = f"{skill['icon']} **{skill['name']} — Learning Roadmap:**\n\n"
    for period, content in skill['roadmap']:
        msg += f"📌 **{period}:** {content}\n"
    msg += f"\n⏱️ **Total time:** {skill['time_to_learn']}\n"
    msg += f"📚 **Resources:** {skill['resources']}"
    return _response(msg, [f"Find {skill['name']} tutor", f"{skill['name']} projects", 'Motivate me'])


# ===== 4. RECOMMENDATIONS =====
def _get_recommendation(msg):
    """Recommend skills based on interest keywords."""
    for interest, skills in RECOMMENDATIONS.items():
        if interest in msg:
            skill_text = '\n'.join([
                f"• {SKILL_DETAILS[s.lower()]['icon']} **{s}** — {SKILL_DETAILS[s.lower()]['difficulty']}"
                for s in skills if s.lower() in SKILL_DETAILS
            ])
            return _response(
                f"🎯 **Recommended for \"{interest}\":**\n\n{skill_text}\n\nAsk about any of these for details or a roadmap!",
                [f"{skills[0]} details", f"{skills[0]} roadmap", 'Other recommendations']
            )

    # Generic recommendation
    return _response(
        "🎯 **Let me help you choose!** What are you interested in?\n\n"
        "• **Coding/Tech** → Python, Data Science, UI Design\n"
        "• **Creative** → Photography, Video Editing, UI Design\n"
        "• **Music** → Guitar, Singing\n"
        "• **Performance** → Dance, Public Speaking\n"
        "• **Business** → Marketing, Public Speaking\n"
        "• **Quick to learn** → Photography, Marketing\n"
        "• **High paying** → Data Science, Python\n"
        "• **Freelance** → Video Editing, UI Design, Photography\n\n"
        "Tell me your interest and I'll recommend the best skill!",
        ['Coding skills', 'Creative skills', 'High paying skills', 'Easy skills']
    )


# ===== 5. TUTOR SEARCH =====
def _find_tutors(msg):
    from .models import Skill, Session

    # Check if specific skill mentioned
    for skill_key in SKILL_DETAILS:
        if skill_key in msg:
            skill = Skill.objects.filter(name__iexact=SKILL_DETAILS[skill_key]['name']).first()
            if skill:
                return _find_tutors_for_skill(skill)

    # Also check DB skills
    skills = Skill.objects.all()
    for skill in skills:
        if skill.name.lower() in msg:
            return _find_tutors_for_skill(skill)

    # No specific skill
    skill_names = ', '.join([s.name for s in skills[:10]])
    return _response(
        f"🔍 Which skill do you need a tutor for?\n\nAvailable: **{skill_names}**\n\nTry: \"Find Python tutor\" or \"Guitar tutor\"",
        [s.name + ' tutor' for s in skills[:4]]
    )


def _find_tutors_for_skill(skill):
    from .models import Session
    sessions = Session.objects.filter(
        skill=skill, status='upcoming'
    ).select_related('tutor', 'tutor__profile').order_by('date', 'start_time')

    if not sessions.exists():
        return _response(
            f"😕 No upcoming **{skill.name}** sessions right now.\n\nCheck back later or [browse all skills](/browse-skills/)!",
            ['Course list', 'Popular skills']
        )

    seen = set()
    tutors = []
    for s in sessions:
        if s.tutor.pk not in seen:
            seen.add(s.tutor.pk)
            p = s.tutor.profile
            tutors.append({
                'id': s.tutor.pk, 'name': s.tutor.get_full_name(),
                'rating': p.average_rating(), 'reviews': p.review_count(),
                'credits': s.credits_required, 'next': s.date.strftime('%b %d'),
                'exp': p.experience_years,
            })

    msg = f"🎓 Found **{len(tutors)} tutor(s)** for **{skill.name}**:\n\n"
    for t in tutors[:5]:
        stars = '⭐' * min(int(t['rating']), 5) if t['rating'] else ''
        msg += f"• **[{t['name']}](/tutor/{t['id']}/)** — {t['rating']}/5 {stars} ({t['reviews']} reviews)"
        if t['exp']:
            msg += f" · {t['exp']}yrs exp"
        msg += f"\n  💰 {t['credits']} credits · Next slot: {t['next']}\n"

    msg += f"\n[Browse all {skill.name} sessions](/browse-skills/?skill={skill.name})"
    return _response(msg, ['How to book', 'My credits', f'{skill.name} roadmap'])


# ===== 8. ENROLLMENT HELP =====
def _get_enrollment_help(msg):
    if any(w in msg for w in ['credit', 'wallet', 'how much', 'cost', 'price', 'free', 'payment']):
        return _response(
            "💰 **Credits & Pricing:**\n\n"
            "• **100 free credits** on signup!\n"
            "• Sessions cost **30-100 credits** depending on tutor\n"
            "• Credits deducted on booking → held in escrow\n"
            "• Released to tutor after both sides confirm\n"
            "• Earn credits by teaching!\n\n"
            "Check balance at [Wallet](/wallet/)",
            ['How to book', 'My credits', 'Become a tutor']
        )

    return _response(
        "📅 **How to Book a Session:**\n\n"
        "1. [Browse Skills](/browse-skills/) or visit a tutor's profile\n"
        "2. Click a **time slot** on the calendar\n"
        "3. Click **Book Now** → credits deducted\n"
        "4. Zoom meeting created → email sent\n"
        "5. Join via Zoom at session time!\n"
        "6. After session → both confirm → credits to tutor\n\n"
        "**Not enough credits?** You'll see a top-up option!",
        ['My credits', 'Find a tutor', 'Popular skills']
    )


# ===== 10. PLATFORM INFO =====
def _get_platform_info(msg):
    if 'feature' in msg:
        return _response(
            "📋 **Skillify Features:**\n\n"
            "• 🔐 Registration + OTP verification\n"
            "• 👤 Tutor/Learner role switching\n"
            "• 📅 Preply-style calendar booking\n"
            "• 🎥 Zoom video integration\n"
            "• 💰 Credit wallet + escrow payments\n"
            "• ✅ Dual confirmation (tutor + learner)\n"
            "• 🚩 Dispute resolution system\n"
            "• ⭐ Rating & review system\n"
            "• 💬 Real-time messaging\n"
            "• 📧 Email notifications\n"
            "• 🌙 Dark mode\n"
            "• 🤖 Chatbot (me!)",
            ['How to book', 'Popular skills', 'Tech stack']
        )

    return _response(
        "🎓 **Skillify** is a peer-to-peer tutoring platform.\n\n"
        "**Learn:** Browse tutors, book 1-on-1 sessions, learn via Zoom.\n"
        "**Teach:** Create sessions, earn credits, build your reputation.\n\n"
        "Everyone gets **100 free credits** on signup. Sessions are via Zoom with a wallet-based credit system.\n\n"
        "Ask me about any skill to get started!",
        ['Course list', 'How to book', 'Popular skills', 'Recommend me a skill']
    )


# ===== PLATFORM STATS =====
def _get_platform_stats():
    from .models import Skill, UserProfile, Session, Booking, Review
    from django.contrib.auth.models import User
    return _response(
        f"📊 **Platform Stats:**\n\n"
        f"• **{User.objects.count()}** users\n"
        f"• **{UserProfile.objects.filter(role='tutor').count()}** tutors\n"
        f"• **{Skill.objects.count()}** skills\n"
        f"• **{Session.objects.filter(status='upcoming').count()}** upcoming sessions\n"
        f"• **{Booking.objects.count()}** bookings\n"
        f"• **{Review.objects.count()}** reviews",
        ['Popular skills', 'Find a tutor', 'Course list']
    )


# ===== 13. HELP =====
def _get_help():
    return _response(
        "🤖 **Hi! I'm Skilly. Here's what I can help with:**\n\n"
        "📚 **\"What is Python?\"** — details about any skill\n"
        "📋 **\"Course list\"** — see all available skills\n"
        "🔥 **\"Popular skills\"** — most booked courses\n"
        "🎯 **\"Recommend me a skill\"** — personalized suggestions\n"
        "📌 **\"Python roadmap\"** — step-by-step learning plan\n"
        "💼 **\"Python career\"** — salary & job info\n"
        "🔍 **\"Find Guitar tutor\"** — search available tutors\n"
        "📅 **\"How to book\"** — enrollment guide\n"
        "💰 **\"My credits\"** — check your balance\n"
        "📜 **\"Certificates\"** — certification options\n"
        "💪 **\"Motivate me\"** — get inspired!\n"
        "ℹ️ **\"What is Skillify?\"** — about the platform\n\n"
        "Just type naturally — I understand! 😊",
        ['Course list', 'Recommend me a skill', 'Popular skills', 'Motivate me']
    )
