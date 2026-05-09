# UniShare

UniShare is a Flask-based web platform that brings University of Western Australia (UWA) students together around the resources they share every semester — second-hand textbooks, study notes, group sessions, paid help bounties, and a lightweight social feed.

Built end-to-end with client-side JavaScript and a server-side Flask + SQLAlchemy stack.

---

## Features

* **Marketplace** — List, browse, search and filter second-hand textbooks; save listings to your library; rate sellers.

* **Notes sharing** — Upload PDF/DOCX/image notes by unit and semester; upvote, save, and download community notes.

* **Study sessions** — Host or RSVP to in-person/online study sessions with capacity limits and locations.

* **Bounties** — Post a reward for help on a tricky assignment; other students can claim and earn.

* **Social feed** — Share posts (general/event/news/resource), like and comment with AJAX, embed link previews and images.

* **Direct messages** — Private 1-on-1 chat between users with AJAX polling for near-real-time delivery.

* **Profiles, ratings & XP** — Earn XP for contributions, climb the leaderboard, see your rank and rating on every profile.

* **Authentication & security** — Salted password hashing (Werkzeug), CSRF protection on every form (Flask-WTF), CSRF tokens attached to all AJAX calls.

* **Responsive UI** — Bootstrap 5 grid and components layered over a custom dark/gold UWA-themed design system in `shared.css`.

---

## Installation

### Prerequisites

* Python 3.10 or newer
* pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/randollz/UniShare.git
cd UniShare

# 2. Create and activate a virtual environment (recommended)
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# macOS / Linux
source venv/bin/activate

# 3. Install runtime dependencies
pip install -r requirements.txt

# 4. Copy the environment template and set a SECRET_KEY
cp .env.example .env

# 5. Initialise the database
flask --app app.py db upgrade

# 6. (Optional) Load demo data
python seed.py
```

---

## Usage

### Run the application

```bash
python app.py
```

Then open:

```text
http://localhost:5000
```

in your browser.

You will land on the public landing page. Click **Sign up** to create an account, or **Login** if you already have one.

After authentication, users are redirected to the dashboard/feed.

### Typical workflow

1. Update your profile and bio in **Settings**.
2. Browse the **Marketplace** for textbooks or post one of your own.
3. Upload **Notes** and earn XP from downloads and saves.
4. Host or join a **Study Session**.
5. Post a **Bounty** when you need help.
6. Share updates on the **Feed**.
7. Message other students directly from their profile.

---

## Testing

The project includes both unit/integration tests and Selenium end-to-end tests.

### Unit and integration tests

```bash
python -m pytest tests/ --ignore=tests/test_selenium.py -v
```

This runs:

* SQLAlchemy model tests
* Validator tests
* Flask route integration tests
* AJAX endpoint tests

(~140 tests total)

### Selenium end-to-end tests

```bash
# Install Selenium dependencies
pip install -r requirements-dev.txt

# Run Selenium suite
python -m pytest tests/test_selenium.py -v
```

The Selenium suite launches a real Flask server and runs browser-based end-to-end tests using a headless Chrome instance.

Tested workflows include:

* Homepage loading
* Login page loading
* User registration
* Login/logout
* Create listing
* Create feed post

### Run all tests

```bash
python -m pytest tests/ -v
```

If Chrome is unavailable, Selenium tests are automatically skipped while the unit suite still runs normally.

---

## Project Structure

```text
UniShare/
├── app.py
├── database.py
├── validators.py
├── seed.py
├── requirements.txt
├── requirements-dev.txt
├── .env.example
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── models.py
│   ├── routes.py
│   ├── controllers.py
│   ├── templates/
│   └── static/
│       ├── css/shared.css
│       └── images/
│
├── migrations/
└── tests/
    ├── test_models.py
    ├── test_routes.py
    ├── test_validators.py
    ├── test_ajax.py
    └── test_selenium.py
```

### Key directories

* `app/` — Main Flask application package
* `templates/` — Jinja2 HTML templates
* `static/` — CSS, JS, uploaded files and images
* `tests/` — Unit, integration and Selenium tests
* `migrations/` — Alembic database migration scripts

---

## License

This project is released under the MIT License.
