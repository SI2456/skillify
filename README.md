# 💡 Skillify — Online Tutoring & E-Learning Platform

> A full-stack Django web application where learners discover skills, find tutors, book sessions, attend live classes via Zoom, and manage credits — with an AI chatbot, real-time messaging, Razorpay payments, and a complete admin panel.

---

## 📋 Table of Contents
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Test Accounts](#-test-accounts)
- [API Endpoints](#-api-endpoints)
- [Project Structure](#-project-structure)
- [Screenshots](#-screenshots)
- [Security](#-security)
- [Future Enhancements](#-future-enhancements)

---

## ✨ Features

### For Learners
- Browse & filter sessions by skill, level, price, rating, date
- Book one-to-one or group sessions
- Join Zoom meetings directly from the platform
- Real-time messaging with tutors (text + file/photo attachments)
- Review & rate tutors (5-star system)
- Credit wallet with Razorpay top-up (₹100/₹500/₹1000 packages)
- File detailed session reports with auto-verification
- Learner profile with skill level & learning interests
- Contact admin support via direct messaging

### For Tutors
- Create sessions with skill, level, date/time, credits
- Weekly recurring availability management with auto-session generation
- Reschedule sessions (45-min rule, learner approval required)
- Upload session materials (PDF/docs) for learners
- Earnings dashboard with Chart.js analytics
- Teaching certificate upload
- Demo video support (YouTube, Vimeo, Google Drive)
- Trust score system (rating + sessions + reviews formula)
- Respond to learner reports with evidence

### Platform Features
- Dual-confirmation payment: both parties confirm before credits release
- 30-minute auto-release if learner doesn't respond
- Dispute resolution system with admin actions
- OTP email verification (branded HTML templates)
- Dark mode on all pages
- AI chatbot (Skilly) with 15 interaction types
- Notification center with real-time polling
- Google OAuth login (django-allauth)
- Mobile responsive design

### Admin Panel (`/panel/`)
- Dashboard with 14 stat cards + recent activity
- User management (search, suspend, delete, make admin)
- Tutor management with trust scores
- Skill management (add/edit/delete)
- Session browser with filters
- Report system with auto-verification scores & flags
- Dispute resolution (refund/release)
- Platform announcements
- Analytics: user growth, booking trends, skill popularity, revenue charts

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.x, Python 3.11+ |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Bootstrap 5, Inter font, vanilla JS |
| Charts | Chart.js 4.x |
| Video | Zoom API (Server-to-Server OAuth) |
| Payments | Razorpay (INR) |
| Auth | django-allauth (Google OAuth) |
| Email | SMTP with HTML templates |
| Real-time | AJAX polling (3s messages, 30s notifications) |

---

## 🏗 Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Learner   │────▶│   Django     │────▶│  SQLite DB  │
│   Browser   │◀────│   Views      │◀────│  (Models)   │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  Zoom    │ │ Razorpay │ │  Gmail   │
        │  API     │ │  API     │ │  SMTP    │
        └──────────┘ └──────────┘ └──────────┘
```

### Data Flow
1. **Booking Flow:** Learner browses → selects slot → credits deducted → tutor notified → Zoom created on start
2. **Payment Flow:** Select package → Razorpay order → checkout popup → signature verified → credits added
3. **Report Flow:** Learner files report → auto-verification (5 flags) → system verdict → admin review → resolution
4. **Dual Confirmation:** Tutor completes → learner confirms → credits released (auto-release after 30 min)

---

## 🚀 Installation

### Prerequisites
- Python 3.11+
- pip

### Setup
```bash
# Clone/extract project
cd skillify_project

# Install dependencies
pip install django djangorestframework django-debug-toolbar requests Pillow PyJWT cryptography django-allauth razorpay

# Run migrations
python manage.py makemigrations core
python manage.py migrate

# Load seed data (10 tutors, 15 skills, sample sessions, reviews)
python manage.py seed_data

# Start server
python manage.py runserver
```

Open: http://127.0.0.1:8000

---

## ⚙️ Configuration

### Environment Variables
```bash
# Zoom (optional)
ZOOM_ACCOUNT_ID=your_account_id
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret

# Razorpay (optional)
RAZORPAY_KEY_ID=rzp_test_xxx
RAZORPAY_KEY_SECRET=xxx

# Google OAuth (optional)
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx

# Email (uses console backend in DEBUG mode)
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```

### Google OAuth Setup
```bash
python manage.py setup_google_auth
```
Or configure manually in Django Admin → Social Applications.

---

## 👤 Test Accounts

| Role | Email | Password |
|------|-------|----------|
| Learner | learner@skillify.com | 123456 |
| Tutor 1 | tutor1@skillify.com | 123456 |
| Tutor 2-10 | tutor2@skillify.com ... tutor10@skillify.com | 123456 |
| Admin | Go to /admin/ | admin / admin123 |

---

## 📡 API Endpoints

### Authentication
| Method | URL | Description |
|--------|-----|-------------|
| GET/POST | `/register/` | User registration |
| GET/POST | `/login/` | Email/password login |
| GET | `/accounts/google/login/` | Google OAuth |
| POST | `/api/check-email/` | AJAX email availability check |

### Sessions & Booking
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/browse-skills/` | Browse with filters |
| POST | `/book/<id>/` | Book a session (AJAX) |
| POST | `/tutor-complete/<id>/` | Tutor marks complete |
| POST | `/reschedule/<id>/` | Tutor reschedule request |

### Payments
| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/create-order/` | Create Razorpay order |
| POST | `/api/verify-payment/` | Verify payment signature |

### Messaging
| Method | URL | Description |
|--------|-----|-------------|
| POST | `/send-message/<id>/` | Send message + file |
| GET | `/fetch-messages/<id>/` | Poll new messages |

### Admin Panel
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/panel/` | Admin dashboard |
| GET | `/panel/api/stats/` | Platform statistics |
| GET | `/panel/api/reports/` | All session reports |
| POST | `/panel/api/report/<id>/action/` | Resolve report |

---

## 📁 Project Structure

```
skillify_project/
├── core/                    # Main Django app
│   ├── models.py           # 14 models (User, Session, Booking, Payment, Report...)
│   ├── views.py            # 40+ views
│   ├── admin_views.py      # Custom admin panel APIs
│   ├── urls.py             # 50+ URL patterns
│   ├── forms.py            # Django forms
│   ├── chatbot.py          # AI chatbot logic (15 types)
│   ├── email_service.py    # HTML email sender
│   ├── zoom_service.py     # Zoom API integration
│   ├── signals.py          # Auto-create profile + wallet
│   └── management/commands/ # seed_data, auto_release, auto_reject
├── templates/
│   ├── core/               # 22 HTML templates
│   └── emails/             # 6 branded email templates
├── static/
│   ├── css/                # 10 CSS files (+ mobile.css)
│   └── js/                 # 9 JS files
└── skillify_project/       # Django settings
```

### Models
| Model | Purpose |
|-------|---------|
| UserProfile | Learner/tutor profiles, trust score, certificates |
| Session | Tutoring sessions with Zoom, levels, materials |
| Booking | Bookings with dual-confirmation, reschedule, disputes |
| Payment | Razorpay payment records |
| SessionReport | Auto-verified reports with 5 fraud flags |
| Notification | In-app notifications |
| Conversation/Message | Real-time messaging with attachments |
| Wallet/Transaction | Credit system with full history |
| TutorAvailability | Weekly recurring schedule |

---

## 🔒 Security

- CSRF protection on all forms
- OTP-based email verification
- Razorpay signature verification (HMAC SHA256)
- User role-based access control (learner/tutor/admin)
- File upload size limits (10MB)
- SQL injection prevention (Django ORM)
- XSS prevention (Django template auto-escaping)
- Session-based authentication
- Password hashing (PBKDF2)

---

## 🚀 Future Enhancements

- [ ] WebSocket real-time messaging (replace AJAX polling)
- [ ] Session recording playback
- [ ] Skill learning roadmaps with progress tracking
- [ ] Tutor verification badge system
- [ ] Tutor payout to bank/UPI
- [ ] PWA (Progressive Web App) support
- [ ] PostgreSQL + Redis for production
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Unit + integration test suite

---

## 👨‍💻 Developer

Built with Django + Bootstrap 5 as a college project demonstrating full-stack web development, payment integration, real-time features, and admin management.

---

*Skillify — Learn, Teach, Grow* 💡
