"""
Configuration loader for the ReachOps cold email tool.

All secrets and environment-specific values live in a `.env` file (see .env.example).
Nothing is ever hardcoded here — this module only defines defaults for the
non-secret contact fields, which can still be overridden via .env.
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


REQUIRED_VARS = [
    "LLM_API_KEY",
    "LLM_PROVIDER",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SENDER_NAME",
    "SENDER_EMAIL",
]


@dataclass
class Config:
    # LLM
    llm_api_key: str
    llm_provider: str
    llm_model: str

    # SMTP
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool

    # Sender identity (the actual "From" address used to send)
    sender_name: str
    sender_email: str

    # Fixed contact block appended to every outgoing email
    contact_name: str
    contact_role: str
    contact_email: str
    contact_phone: str
    contact_portfolio: str

    # Runtime behaviour
    max_concurrency: int
    db_path: str


def load_config() -> Config:
    """Load and validate configuration from environment variables (.env).

    Raises:
        ConfigError: if any required variable is missing.
    """
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        raise ConfigError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Copy .env.example to .env and fill in the values."
        )

    try:
        smtp_port = int(os.getenv("SMTP_PORT"))
    except (TypeError, ValueError):
        raise ConfigError("SMTP_PORT must be a valid integer.")

    return Config(
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_provider=os.getenv("LLM_PROVIDER"),
        llm_model=os.getenv("LLM_MODEL", ""),

        smtp_host=os.getenv("SMTP_HOST"),
        smtp_port=smtp_port,
        smtp_username=os.getenv("SMTP_USERNAME"),
        smtp_password=os.getenv("SMTP_PASSWORD"),
        smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").lower() != "false",

        sender_name=os.getenv("SENDER_NAME"),
        sender_email=os.getenv("SENDER_EMAIL"),

        contact_name=os.getenv("CONTACT_NAME", "Vyakhya Goyal"),
        contact_role=os.getenv("CONTACT_ROLE", "Product Manager | ReachOps"),
        contact_email=os.getenv("CONTACT_EMAIL", "support.reachops@gmail.com"),
        contact_phone=os.getenv("CONTACT_PHONE", "+91 7746985352"),
        contact_portfolio=os.getenv(
            "CONTACT_PORTFOLIO", "https://my-portfolio-mushan-khan.vercel.app/"
        ),

        max_concurrency=int(os.getenv("MAX_CONCURRENCY", "1")),
        db_path=os.getenv("DB_PATH", "reachops_outreach.db"),
    )
