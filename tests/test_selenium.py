"""End-to-end (Selenium) tests against a live Flask server.

These tests start a real Flask app in a background thread on a free port,
drive a headless Chrome browser through realistic user flows, and assert
the rendered UI behaves correctly.

Run them:
    pip install -r requirements-dev.txt
    pytest tests/test_selenium.py -v

The whole module is skipped automatically if Selenium / Chrome is not
available, so it does not break ``pytest tests/`` for developers who only
run the unit suite.
"""
import os
import socket
import threading
import time

import pytest

# If selenium is not installed, skip this entire module.
selenium = pytest.importorskip("selenium")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service as ChromeService
    HAS_WDM = True
except ImportError:
    HAS_WDM = False

from werkzeug.serving import make_server

from app import create_app
from app.extensions import db as _db
from app.models import User
from app.config import Config


# ─────────────────────────────────────────────────────────────────────────
# Test configuration
# ─────────────────────────────────────────────────────────────────────────

class SeleniumTestConfig(Config):
    """Config for the live test server: file-backed SQLite, CSRF on."""
    TESTING = True
    SECRET_KEY = "selenium-test-secret"
    WTF_CSRF_ENABLED = True
    # Resolved per-session in the live_server fixture so each session gets a
    # fresh database file.
    SQLALCHEMY_DATABASE_URI = "sqlite:///selenium_test.db"


def _free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


def _wait_until_listening(host: str, port: int, timeout: float = 5.0):
    """Block until the server starts accepting TCP connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.1):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"server on {host}:{port} did not start within {timeout}s")


# ─────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def live_server():
    """Spin up a real Flask app on a free localhost port for the test session."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    db_path = os.path.join(project_root, "selenium_test.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    # Ensure the SQLite URI uses an absolute path so the path is independent of cwd.
    SeleniumTestConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///" + db_path

    app = create_app(config_class=SeleniumTestConfig)

    # Seed one known user we can log in as in later tests.
    with app.app_context():
        _db.create_all()
        u = User(
            first_name="Selenium",
            last_name="User",
            email="selenium@test.com",
            password_hash="",
        )
        u.set_password("test1234")
        _db.session.add(u)
        _db.session.commit()

    port = _free_port()
    server = make_server("localhost", port, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _wait_until_listening("localhost", port)

    yield f"http://localhost:{port}"

    server.shutdown()
    thread.join(timeout=5)
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


@pytest.fixture(scope="session")
def driver():
    """Headless Chrome driver. Skips the module if Chrome is unavailable."""
    if not HAS_WDM:
        pytest.skip("webdriver-manager not installed; pip install -r requirements-dev.txt")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")

    try:
        service = ChromeService(ChromeDriverManager().install())
        drv = webdriver.Chrome(service=service, options=options)
    except WebDriverException as exc:
        pytest.skip(f"Chrome / chromedriver unavailable: {exc}")

    drv.implicitly_wait(2)
    yield drv
    drv.quit()


@pytest.fixture
def browser(driver, live_server):
    """Per-test driver: clears cookies before/after so tests are isolated."""
    driver.get(live_server)
    driver.delete_all_cookies()
    yield driver
    driver.delete_all_cookies()


# ─────────────────────────────────────────────────────────────────────────
# Helpers used by tests in commit 2 (kept here so all flows share them)
# ─────────────────────────────────────────────────────────────────────────

def wait_for(driver, selector, by=By.CSS_SELECTOR, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )


def login_user(driver, base_url, email="selenium@test.com", password="test1234"):
    driver.get(f"{base_url}/login")
    wait_for(driver, "input[name=\"email\"]").send_keys(email)
    driver.find_element(By.CSS_SELECTOR, "input[name=\"password\"]").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type=\"submit\"]").click()
    WebDriverWait(driver, 10).until(EC.url_contains("/dashboard"))


# ─────────────────────────────────────────────────────────────────────────
# Smoke tests (commit 1)
# ─────────────────────────────────────────────────────────────────────────

class TestSmoke:
    def test_homepage_loads(self, browser, live_server):
        """Home page renders and contains the UniShare brand."""
        browser.get(live_server + "/")
        assert "UniShare" in browser.title or "UniShare" in browser.page_source

    def test_login_page_loads(self, browser, live_server):
        """Login page renders with both email and password fields visible."""
        browser.get(live_server + "/login")
        wait_for(browser, "input[name=\"email\"]")
        wait_for(browser, "input[name=\"password\"]")
        assert "Sign in" in browser.page_source or "Log in" in browser.page_source



# ─────────────────────────────────────────────────────────────────────────
# Functional flow tests (commit 2)
# ─────────────────────────────────────────────────────────────────────────

class TestAuthFlows:
    def test_register_new_user_redirects_to_dashboard(self, browser, live_server):
        """Sign-up form on /login creates an account and lands on /dashboard."""
        browser.get(f"{live_server}/login")

        # Switch to the Create-account tab (custom JS toggle on this page)
        browser.execute_script(
            "document.querySelectorAll(\".auth-tab\")[1].click();"
        )

        # Wait for the signup view to become visible (signup form has first_name)
        wait_for(browser, "#signup-view input[name=\"first_name\"]")

        # Fill in the registration form (signup-view scope so we don't pick up
        # the hidden login form)
        signup = browser.find_element(By.CSS_SELECTOR, "#signup-view")
        signup.find_element(By.CSS_SELECTOR, "input[name=\"first_name\"]").send_keys("Alice")
        signup.find_element(By.CSS_SELECTOR, "input[name=\"last_name\"]").send_keys("E2E")
        signup.find_element(By.CSS_SELECTOR, "input[name=\"email\"]").send_keys("alice_e2e@test.com")
        signup.find_element(By.CSS_SELECTOR, "input[name=\"password\"]").send_keys("testpass1")
        signup.find_element(By.CSS_SELECTOR, "button[type=\"submit\"]").click()

        WebDriverWait(browser, 10).until(EC.url_contains("/dashboard"))
        assert "/dashboard" in browser.current_url

    def test_login_then_logout(self, browser, live_server):
        """Login as the seed user and log out — final URL should leave dashboard."""
        login_user(browser, live_server)
        assert "/dashboard" in browser.current_url

        # Hit the logout endpoint directly (link is in the sidebar; this is
        # more robust against layout changes)
        browser.get(f"{live_server}/logout")
        WebDriverWait(browser, 10).until(
            lambda d: "/dashboard" not in d.current_url
        )
        assert "/dashboard" not in browser.current_url


class TestContentCreation:
    def test_create_listing_appears_in_marketplace(self, browser, live_server):
        """Create a listing through /create_listing and verify it shows in marketplace."""
        login_user(browser, live_server)

        unique_title = f"Selenium Textbook {int(time.time())}"
        browser.get(f"{live_server}/create_listing")

        wait_for(browser, "input[name=\"title\"]").send_keys(unique_title)
        browser.find_element(By.CSS_SELECTOR, "input[name=\"unit_code\"]").send_keys("CITS3403")
        browser.find_element(By.CSS_SELECTOR, "input[name=\"price\"]").send_keys("19.99")
        browser.find_element(By.CSS_SELECTOR, "textarea[name=\"description\"]").send_keys(
            "End-to-end test listing"
        )
        browser.find_element(By.CSS_SELECTOR, "button[type=\"submit\"]").click()

        # After submit, should land on marketplace (or wherever the route redirects)
        WebDriverWait(browser, 10).until(
            lambda d: "/create_listing" not in d.current_url
        )

        # Visit the marketplace and confirm our title shows up
        browser.get(f"{live_server}/marketplace")
        wait_for(browser, ".lc-title")
        assert unique_title in browser.page_source

    def test_create_post_appears_in_feed(self, browser, live_server):
        """Submit a post via the dashboard compose form — it should show in the feed."""
        login_user(browser, live_server)

        unique_body = f"Selenium e2e post {int(time.time())}"
        browser.get(f"{live_server}/dashboard")

        # Some templates render the textarea inside an inline compose box
        textarea = wait_for(browser, "textarea[name=\"body\"]")
        textarea.send_keys(unique_body)

        # Submit the compose form
        browser.execute_script(
            "document.getElementById(\"compose-form\").submit();"
        )

        # Wait for navigation back to dashboard / feed
        WebDriverWait(browser, 10).until(
            lambda d: unique_body in d.page_source
        )
        assert unique_body in browser.page_source
