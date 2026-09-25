import os
from dotenv import load_dotenv

load_dotenv(".env")

class Config:
    BASE_URL = os.getenv("BASE_URL", "https://your-api-url.com")
    AUTH_URL = os.getenv("AUTH_URL", "https://your-api-url.com/auth")
    TEST_USERNAME = os.getenv("TEST_USERNAME", "your_username_here")
    TEST_PASSWORD = os.getenv("TEST_PASSWORD", "your_password_here")
    TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "30000"))
    ACTION_TIMEOUT = int(os.getenv("ACTION_TIMEOUT", "10000"))
    AUTH_TIMEOUT = int(os.getenv("AUTH_TIMEOUT", "45000"))
    NETWORK_IDLE_TIMEOUT = int(os.getenv("NETWORK_IDLE_TIMEOUT", "5000"))
    WAIT_FOR_SELECTOR_TIMEOUT = int(os.getenv("WAIT_FOR_SELECTOR_TIMEOUT", "10000"))
    BROWSER = os.getenv("BROWSER", "chromium")
    HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
    VIEWPORT_WIDTH = int(os.getenv("VIEWPORT_WIDTH", "1600"))
    VIEWPORT_HEIGHT = int(os.getenv("VIEWPORT_HEIGHT", "1200"))
    LOCALE = os.getenv("LOCALE", "ru-RU")
    WAIT_UNTIL = os.getenv("WAIT_UNTIL", "domcontentloaded")
    REPORT_FOLDER = os.getenv("REPORT_FOLDER", "playwright-report")
