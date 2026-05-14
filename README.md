# UniShare

> A student resource-sharing platform for the University of Western Australia.

UniShare brings UWA students together around the resources they share every semester — second-hand textbooks, study notes, group sessions, paid help bounties, and a lightweight social feed.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## Features

| Feature | Description |
|---------|-------------|
| **Marketplace** | List, browse, search and filter second-hand textbooks; save listings to your library; rate sellers |
| **Notes Sharing** | Upload PDF/DOCX/image notes by unit and semester; upvote, save, and download community notes |
| **Study Sessions** | Host or RSVP to in-person/online study sessions with capacity limits and locations |
| **Bounties** | Post an XP reward for help on a tricky assignment; other students can claim and earn |
| **Social Feed** | Share posts (general / event / news / resource), like and comment, embed images |
| **Universal Search** | Search across listings, notes, sessions, and bounties from the nav bar |
| **Direct Messages** | Private 1-on-1 chat between users with near-real-time AJAX polling |
| **Profiles & XP** | Earn XP for contributions, climb the leaderboard, see rank and rating on every profile |
| **Authentication** | Salted password hashing (Werkzeug), CSRF protection on every form (Flask-WTF) |
| **Responsive UI** | Bootstrap 5 layered over a custom UWA-themed design system |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3, Flask, SQLAlchemy, Flask-Login, Flask-WTF |
| Database | SQLite (development), configurable via `DATABASE_URL` |
| Migrations | Flask-Migrate (Alembic) |
| Frontend | Bootstrap 5, vanilla JS, Font Awesome 6 |
| Templating | Jinja2 |
| Testing | pytest, unittest, Selenium (optional E2E) |

---

## Getting Started

### Prerequisites

- Python 3.10 or newer
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/randollz/UniShare.git
cd UniShare

# 2. Create and activate a virtual environment
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the environment template
cp .env.example .env

# 5. Initialise the database
flask --app app.py db upgrade

# 6. (Optional) Load demo data
python seed.py
```

### Environment Variables

Copy `.env.example` to `.env` and set the following:

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Long random string used for session signing and CSRF tokens |
| `DATABASE_URL` | No | SQLAlchemy connection string — defaults to `sqlite:///app.db` |

Generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## Usage

Start the development server:

```bash
python app.py
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

You will land on the public home page. Click **Sign up** to create an account or **Log in** if you already have one. After authentication you are redirected to the dashboard feed.

### Typical workflow

1. Update your profile and bio in **Settings**
2. Browse the **Marketplace** for textbooks, or list one of your own
3. Upload **Notes** and earn XP from downloads and upvotes
4. Host or join a **Study Session**
5. Post a **Bounty** when you need assignment help
6. Share updates on the **Feed**
7. Use the **Search** bar to find content across the entire platform
8. Message other students directly from their profile

---

## Testing

The project includes unit tests, integration tests, and optional Selenium end-to-end tests.

### Unit and integration tests

```bash
python -m pytest tests/ --ignore=tests/test_selenium.py -v
```

This runs 156 tests covering:

- SQLAlchemy model tests (`test_models.py`)
- Input validator tests (`test_validators.py`)
- Flask route integration tests (`test_routes.py`)
- AJAX endpoint tests (`test_ajax.py`)

### Selenium end-to-end tests

Selenium requires Chrome and `webdriver-manager`:

```bash
pip install selenium webdriver-manager
python -m pytest tests/test_selenium.py -v
```

The Selenium suite launches a real Flask server and drives a headless Chrome browser through the following flows:

- Homepage and login page loading
- User registration
- Login and logout
- Create a listing and verify it appears in the marketplace
- Create a feed post and verify it appears in the feed

If Chrome is unavailable the Selenium suite is automatically skipped while the unit tests continue to run normally.

### Run everything

```bash
python -m pytest tests/ -v
```

---

## Project Structure

```text
UniShare/
├── app.py                  # Application entry point
├── seed.py                 # Demo data seeder
├── requirements.txt        # Runtime dependencies
├── .env.example            # Environment variable template
│
├── app/
│   ├── __init__.py         # App factory (create_app)
│   ├── config.py           # Configuration classes
│   ├── extensions.py       # Flask extensions (db, login_manager, csrf)
│   ├── models.py           # SQLAlchemy models
│   ├── controllers.py      # Business logic helpers
│   ├── validators.py       # Input validation utilities
│   ├── routes/             # Route handlers split by domain
│   │   ├── auth.py         # Login, logout
│   │   ├── main.py         # Home, leaderboard, search
│   │   ├── listings.py     # Marketplace, create/save/delete listings
│   │   ├── notes.py        # Notes, upload, download
│   │   ├── sessions.py     # Study sessions, RSVP
│   │   ├── bounties.py     # Bounties, claim, delete
│   │   ├── feed.py         # Dashboard, posts, likes, comments
│   │   ├── messages.py     # Direct messaging
│   │   └── users.py        # Profiles, settings, activity
│   ├── templates/          # Jinja2 HTML templates
│   └── static/
│       ├── css/shared.css  # Global design system
│       └── images/         # Static assets
│
├── migrations/             # Alembic migration scripts
└── tests/
    ├── conftest.py         # Shared pytest fixtures
    ├── test_models.py      # Model unit tests
    ├── test_routes.py      # Route integration tests
    ├── test_ajax.py        # AJAX endpoint tests
    ├── test_validators.py  # Validator unit tests
    └── test_selenium.py    # Selenium E2E tests
```

---

## Contributing

This project is developed as a group assignment for CITS3403 at UWA.

1. Branch off `main` using the convention `feature/<short-description>` or `fix/<short-description>`
2. Make your changes and ensure all tests pass: `python -m pytest tests/ --ignore=tests/test_selenium.py`
3. Open a pull request against `main` with a clear description of what changed and why
4. Request a review from a team member before merging

---

## License

This project is released under the [MIT License](LICENSE).
