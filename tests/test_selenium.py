"""End-to-end (Selenium) tests against a live Flask server.

These tests start a real Flask app in a background thread on a free port,
drive a headless Chrome browser through realistic user flows, and assert
the rendered UI behaves correctly.

Run them:
    pytest tests/test_selenium.py -v

The whole suite is skipped automatically if Selenium / Chrome is not
available, so it does not break ``pytest tests/`` for developers who only
run the unit suite.
"""
import os
import socket
import threading
import time
import unittest

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

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
    SQLALCHEMY_DATABASE_URI = "sqlite:///selenium_test.db"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


def _wait_until_listening(host: str, port: int, timeout: float = 5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.1):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"server on {host}:{port} did not start within {timeout}s")


def _make_driver():
    """Return a headless Chrome driver, or None if unavailable."""
    if not SELENIUM_AVAILABLE or not HAS_WDM:
        return None
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    try:
        service = ChromeService(ChromeDriverManager().install())
        drv = webdriver.Chrome(service=service, options=options)
        drv.implicitly_wait(2)
        return drv
    except WebDriverException:
        return None


def _start_server(db_path):
    """Create, seed, and start a Flask test server. Returns (server, thread, base_url)."""
    if os.path.exists(db_path):
        os.remove(db_path)

    SeleniumTestConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///" + db_path
    app = create_app(config_class=SeleniumTestConfig)

    with app.app_context():
        _db.create_all()
        u = User(first_name="Selenium", last_name="User",
                 email="selenium@test.com", password_hash="")
        u.set_password("test1234")
        _db.session.add(u)
        _db.session.commit()

    port = _free_port()
    server = make_server("localhost", port, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _wait_until_listening("localhost", port)
    return server, thread, f"http://localhost:{port}"


def _stop_server(server, thread, db_path):
    server.shutdown()
    thread.join(timeout=5)
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

def wait_for(driver, selector, by=None, timeout=10):
    if by is None:
        by = By.CSS_SELECTOR
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )


def login_user(driver, base_url, email="selenium@test.com", password="test1234"):
    driver.get(f"{base_url}/login")
    wait_for(driver, "login-email", by=By.ID).send_keys(email)
    driver.find_element(By.ID, "login-password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type=\"submit\"]").click()
    WebDriverWait(driver, 10).until(EC.url_contains("/dashboard"))


# ─────────────────────────────────────────────────────────────────────────
# Smoke tests
# ─────────────────────────────────────────────────────────────────────────

@unittest.skipUnless(SELENIUM_AVAILABLE and HAS_WDM, "Selenium/ChromeDriver not installed")
class TestSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        cls._db_path = os.path.join(project_root, "selenium_smoke_test.db")
        cls._server, cls._thread, cls.base_url = _start_server(cls._db_path)
        cls.driver = _make_driver()
        if cls.driver is None:
            raise unittest.SkipTest("Chrome/chromedriver unavailable")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        _stop_server(cls._server, cls._thread, cls._db_path)

    def setUp(self):
        self.driver.delete_all_cookies()

    def tearDown(self):
        self.driver.delete_all_cookies()

    def test_homepage_loads(self):
        """Home page renders and contains the UniShare brand."""
        self.driver.get(self.base_url + "/")
        self.assertTrue(
            "UniShare" in self.driver.title or "UniShare" in self.driver.page_source,
            "Homepage should contain the UniShare brand in title or page source"
        )

    def test_login_page_loads(self):
        """Login page renders with both email and password fields visible."""
        self.driver.get(self.base_url + "/login")
        wait_for(self.driver, "login-email", by=By.ID)
        wait_for(self.driver, "login-password", by=By.ID)
        self.assertTrue(
            "Sign in" in self.driver.page_source or "Log in" in self.driver.page_source,
            "Login page should contain 'Sign in' or 'Log in' text"
        )


# ─────────────────────────────────────────────────────────────────────────
# Auth flow tests
# ─────────────────────────────────────────────────────────────────────────

@unittest.skipUnless(SELENIUM_AVAILABLE and HAS_WDM, "Selenium/ChromeDriver not installed")
class TestAuthFlows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        cls._db_path = os.path.join(project_root, "selenium_auth_test.db")
        cls._server, cls._thread, cls.base_url = _start_server(cls._db_path)
        cls.driver = _make_driver()
        if cls.driver is None:
            raise unittest.SkipTest("Chrome/chromedriver unavailable")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        _stop_server(cls._server, cls._thread, cls._db_path)

    def setUp(self):
        self.driver.delete_all_cookies()

    def tearDown(self):
        self.driver.delete_all_cookies()

    def test_register_new_user_redirects_to_dashboard(self):
        """Sign-up form on /login creates an account and lands on /dashboard."""
        self.driver.get(f"{self.base_url}/login")

        self.driver.execute_script(
            "document.querySelectorAll(\".auth-tab\")[1].click();"
        )

        wait_for(self.driver, "signup-first-name", by=By.ID)

        self.driver.find_element(By.ID, "signup-first-name").send_keys("Alice")
        self.driver.find_element(By.ID, "signup-last-name").send_keys("E2E")
        self.driver.find_element(By.ID, "signup-email").send_keys("alice_e2e@test.com")
        self.driver.find_element(By.ID, "signup-password").send_keys("testpass1")
        self.driver.find_element(By.CSS_SELECTOR, "#signup-view button[type=\"submit\"]").click()

        WebDriverWait(self.driver, 10).until(EC.url_contains("/dashboard"))
        self.assertIn("/dashboard", self.driver.current_url,
                      "Registration should redirect to /dashboard")

    def test_login_then_logout(self):
        """Login as the seed user and log out — final URL should leave dashboard."""
        login_user(self.driver, self.base_url)
        self.assertIn("/dashboard", self.driver.current_url,
                      "Login should redirect to /dashboard")

        self.driver.get(f"{self.base_url}/logout")
        WebDriverWait(self.driver, 10).until(
            lambda d: "/dashboard" not in d.current_url
        )
        self.assertNotIn("/dashboard", self.driver.current_url,
                         "After logout, user should not be on /dashboard")


# ─────────────────────────────────────────────────────────────────────────
# Content creation tests
# ─────────────────────────────────────────────────────────────────────────

@unittest.skipUnless(SELENIUM_AVAILABLE and HAS_WDM, "Selenium/ChromeDriver not installed")
class TestContentCreation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        cls._db_path = os.path.join(project_root, "selenium_content_test.db")
        cls._server, cls._thread, cls.base_url = _start_server(cls._db_path)
        cls.driver = _make_driver()
        if cls.driver is None:
            raise unittest.SkipTest("Chrome/chromedriver unavailable")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        _stop_server(cls._server, cls._thread, cls._db_path)

    def setUp(self):
        self.driver.delete_all_cookies()

    def tearDown(self):
        self.driver.delete_all_cookies()

    def test_create_listing_appears_in_marketplace(self):
        """Create a listing through /create_listing and verify it shows in marketplace."""
        login_user(self.driver, self.base_url)

        unique_title = f"Selenium Textbook {int(time.time())}"
        self.driver.get(f"{self.base_url}/create_listing")

        wait_for(self.driver, "input[name=\"title\"]").send_keys(unique_title)
        self.driver.find_element(By.CSS_SELECTOR, "input[name=\"unit_code\"]").send_keys("CITS3403")
        self.driver.find_element(By.CSS_SELECTOR, "input[name=\"price\"]").send_keys("19.99")
        self.driver.find_element(By.CSS_SELECTOR, "textarea[name=\"description\"]").send_keys(
            "End-to-end test listing"
        )
        self.driver.find_element(By.CSS_SELECTOR, "button[type=\"submit\"]").click()

        WebDriverWait(self.driver, 10).until(
            lambda d: "/create_listing" not in d.current_url
        )

        self.driver.get(f"{self.base_url}/marketplace")
        wait_for(self.driver, ".lc-title")
        self.assertIn(unique_title, self.driver.page_source,
                      "Created listing should appear in marketplace page source")

    def test_create_post_appears_in_feed(self):
        """Submit a post via the dashboard compose form — it should show in the feed."""
        login_user(self.driver, self.base_url)

        unique_body = f"Selenium e2e post {int(time.time())}"
        self.driver.get(f"{self.base_url}/dashboard")

        textarea = wait_for(self.driver, "textarea[name=\"body\"]")
        textarea.send_keys(unique_body)

        self.driver.execute_script(
            "document.getElementById(\"compose-form\").submit();"
        )

        WebDriverWait(self.driver, 10).until(
            lambda d: unique_body in d.page_source
        )
        self.assertIn(unique_body, self.driver.page_source,
                      "Created post should appear in the feed")
