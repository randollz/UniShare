# UniShare

UniShare is a Flask-based web platform that brings University of Western
Australia (UWA) students together around the resources they share every
semester &mdash; second-hand textbooks, study notes, group sessions, paid
help bounties, and a lightweight social feed. Built end-to-end with
client-side JavaScript and a server-side Flask + SQLAlchemy stack.

---

## Features

- **Marketplace** &mdash; List, browse, search and filter second-hand
  textbooks; save listings to your library; rate sellers.
- **Notes sharing** &mdash; Upload PDF/DOCX/image notes by unit and
  semester; upvote, save, and download community notes.
- **Study sessions** &mdash; Host or RSVP to in-person/online study
  sessions with capacity limits and locations.
- **Bounties** &mdash; Post a reward for help on a tricky assignment;
  other students can claim and earn.
- **Social feed** &mdash; Share posts (general/event/news/resource),
  like and comment with AJAX, embed link previews and images.
- **Direct messages** &mdash; Private 1-on-1 chat between users with
  AJAX polling for near-real-time delivery.
- **Profiles, ratings &amp; XP** &mdash; Earn XP for contributions,
  climb the leaderboard, see your rank and rating on every profile.
- **Authentication &amp; security** &mdash; Salted password hashing
  (Werkzeug), CSRF protection on every form (Flask-WTF), CSRF tokens
  attached to all AJAX calls.
- **Responsive UI** &mdash; Bootstrap 5 grid + components layered over
  a custom dark/gold UWA-themed design system in `shared.css`.

---

## Installation

### Prerequisites

- Python 3.10 or newer
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/randollz/UniShare.git
cd UniShare

# 2. Create and activate a virtual environment (recommended)
python -m venv venv

#    Windows (PowerShell):
.\venv\Scripts\Activate.ps1
#    macOS / Linux:
source venv/bin/activate

# 3. Install runtime dependencies
pip install -r requirements.txt

# 4. Copy the environment template and set a SECRET_KEY
cp .env.example .env
# (then open .env and replace the placeholder SECRET_KEY)

# 5. Initialise the database
flask --app app.py db upgrade

# 6. (Optional) Load demo data so the app isn't empty on first run
python seed.py
```

---

## Usage

### Run the application

```bash
python app.py
```

Then open <http://localhost:5000> in your browser. You will land on the
public landing page; click **Sign up** to create an account, or **Log
in** if you already have one. After authenticating you are taken to the
dashboard / feed.

A typical workflow:

1. Update your profile and bio in **Settings**.
2. Browse the **Marketplace** for textbooks or post one of your own
   from **My Listings &rarr; New Listing**.
3. Upload **Notes** (PDF, DOCX or images) and earn XP every time
   another student saves or downloads them.
4. Host or join a **Study Session**, or post a **Bounty** when you
   need help.
5. Share an update on the **Feed** &mdash; include an image or a
   shareable link.
6. **Message** other students directly from their profile.

### Run the tests

The project ships with two test layers.

**1. Unit and integration tests (fast, no browser required):**

```bash
python -m pytest tests/ --ignore=tests/test_selenium.py -v
```

This runs the SQLAlchemy model tests, validator tests, Flask route
integration tests and AJAX endpoint tests &mdash; ~140 tests in total.

**2. End-to-end Selenium tests (requires Chrome installed locally):**

```bash
# Install test-only extras (Selenium + webdriver-manager)
pip install -r requirements-dev.txt

# Run the Selenium suite
python -m pytest tests/test_selenium.py -v
```

The Selenium suite spins up a real Flask server on a free localhost
port in a background thread, then drives a **headless** Chrome browser
through six end-to-end user journeys (homepage, login page, sign-up,
login &amp; logout, create listing, create post). The first run will
auto-download a matching `chromedriver` &mdash; subsequent runs are
cached.

To run **everything** in one go:

```bash
python -m pytest tests/ -v
```

If Chrome is not installed, the Selenium module is automatically
skipped &mdash; the unit suite still runs.

---

## Project structure

```
UniShare/
├── app.py                    # Flask entry point
├── database.py               # DB initialisation helpers
├── validators.py             # Reusable form-validation utilities
├── seed.py                   # Optional demo-data loader
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Test-only extras (Selenium)
├── .env.example              # Environment variable template
│
├── app/
│   ├── __init__.py           # Flask app factory + extension wiring
│   ├── config.py             # Config (SECRET_KEY, DB URI, CSRF)
│   ├── extensions.py         # db, migrate, login_manager, csrf
│   ├── models.py             # SQLAlchemy models
│   ├── routes.py             # All HTTP route handlers
│   ├── controllers.py        # Business logic shared by routes
│   ├── templates/            # Jinja2 templates (one per page)
│   └── static/
│       ├── css/shared.css    # Custom design system (dark + gold)
│       └── images/           # Banners, textbook covers, uploads
│
├── migrations/               # Alembic database migration scripts
│
└── tests/
    ├── test_models.py        # ORM model unit tests
    ├── test_routes.py        # Flask route integration tests
    ├── test_validators.py    # Input-validation unit tests
    ├── test_ajax.py          # JSON-endpoint tests
    └── test_selenium.py      # End-to-end browser tests
```

---

## License

This project is released under the [MIT License](https://opensource.org/licenses/MIT).
