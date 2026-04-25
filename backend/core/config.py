import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_csv(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None:
        return default
    values = [v.strip() for v in raw.split(",") if v.strip()]
    return values or default


def _get_nested(config: dict[str, Any], keys: list[str], default: Any) -> Any:
    current: Any = config
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_csv_list(value: Any, default: list[str]) -> list[str]:
    if isinstance(value, list):
        values = [str(v).strip() for v in value if str(v).strip()]
        return values or default
    if isinstance(value, str):
        values = [v.strip() for v in value.split(",") if v.strip()]
        return values or default
    return default


def _to_path(value: Any, base_dir: Path) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _load_yaml_config(config_path: Path) -> dict[str, Any]:
    if yaml is None or not config_path.exists():
        return {}

    try:
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

    return loaded if isinstance(loaded, dict) else {}


_CORE_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _CORE_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

# Load project .env once so all services can read runtime configuration.
load_dotenv(_PROJECT_ROOT / ".env")


class Settings:
    def __init__(self) -> None:
        config_path_raw = os.getenv("SETTINGS_YAML_PATH", str(_CORE_DIR / "settings.yml"))
        self.SETTINGS_YAML_PATH: Path = _to_path(config_path_raw, _PROJECT_ROOT)
        self._yaml: dict[str, Any] = _load_yaml_config(self.SETTINGS_YAML_PATH)

        # App
        self.APP_NAME: str = os.getenv(
            "APP_NAME",
            str(_get_nested(self._yaml, ["app", "name"], "Workspace API")),
        )
        self.APP_VERSION: str = os.getenv(
            "APP_VERSION",
            str(_get_nested(self._yaml, ["app", "version"], "1.0.0")),
        )
        self.DEBUG: bool = _env_bool(
            "DEBUG",
            _to_bool(_get_nested(self._yaml, ["app", "debug"], False), False),
        )
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            str(_get_nested(self._yaml, ["app", "database_url"], "sqlite:///./app.db")),
        )
        self.JWT_SECRET_KEY: str = os.getenv(
            "JWT_SECRET_KEY",
            str(_get_nested(self._yaml, ["auth", "jwt_secret_key"], "change-this-in-production")),
        )
        self.JWT_ALGORITHM: str = os.getenv(
            "JWT_ALGORITHM",
            str(_get_nested(self._yaml, ["auth", "jwt_algorithm"], "HS256")),
        )
        self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = _env_int(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
            _to_int(_get_nested(self._yaml, ["auth", "access_token_expire_minutes"], 60), 60),
        )
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.CORS_ALLOW_ORIGINS: list[str] = _env_csv(
            "CORS_ALLOW_ORIGINS",
            _to_csv_list(
                _get_nested(
                    self._yaml,
                    ["app", "cors_allow_origins"],
                    [
                        "http://localhost:5173",
                        "http://127.0.0.1:5173",
                    ],
                ),
                [
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                ],
            ),
        )

        # Storage / metadata backends
        self.STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "azure_blob")
        self.METADATA_STORE: str = os.getenv("METADATA_STORE", "mongodb")
        self.AZURE_STORAGE_CONNECTION_STRING: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
        self.AZURE_STORAGE_CONTAINER_NAME: str = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "")
        self.MONGODB_URI: str = os.getenv("MONGODB_URI", "")
        self.MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "ai_knowledge_system")
        self.MONGODB_DOCUMENTS_COLLECTION: str = os.getenv("MONGODB_DOCUMENTS_COLLECTION", "documents")
        self.MONGODB_INGESTION_JOBS_COLLECTION: str = os.getenv(
            "MONGODB_INGESTION_JOBS_COLLECTION",
            "ingestion_jobs",
        )
        self.MONGODB_DOCUMENT_CHUNKS_COLLECTION: str = os.getenv(
            "MONGODB_DOCUMENT_CHUNKS_COLLECTION",
            "document_chunks",
        )
        self.MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = _env_int(
            "MONGODB_SERVER_SELECTION_TIMEOUT_MS",
            5000,
        )

        # Paths
        self.PROJECT_ROOT: Path = _to_path(
            os.getenv(
                "PROJECT_ROOT",
                str(_get_nested(self._yaml, ["paths", "project_root"], _PROJECT_ROOT)),
            ),
            _PROJECT_ROOT,
        )
        self.BACKEND_DIR: Path = _to_path(
            os.getenv(
                "BACKEND_DIR",
                str(_get_nested(self._yaml, ["paths", "backend_dir"], _BACKEND_DIR)),
            ),
            self.PROJECT_ROOT,
        )
        self.SECRETS_DIR: Path = _to_path(
            os.getenv(
                "SECRETS_DIR",
                str(_get_nested(self._yaml, ["paths", "secrets_dir"], self.BACKEND_DIR / "secrets")),
            ),
            self.PROJECT_ROOT,
        )

        # Google Calendar
        self.GOOGLE_CALENDAR_CREDENTIALS_PATH: Path = _to_path(
            os.getenv(
                "GOOGLE_CALENDAR_CREDENTIALS_PATH",
                str(
                    _get_nested(
                        self._yaml,
                        ["google_calendar", "credentials_path"],
                        self.SECRETS_DIR / "credentials.json",
                    )
                ),
            ),
            self.PROJECT_ROOT,
        )
        self.GOOGLE_CALENDAR_TOKEN_PATH: Path = _to_path(
            os.getenv(
                "GOOGLE_CALENDAR_TOKEN_PATH",
                str(
                    _get_nested(
                        self._yaml,
                        ["google_calendar", "token_path"],
                        self.SECRETS_DIR / "token.json",
                    )
                ),
            ),
            self.PROJECT_ROOT,
        )
        self.GOOGLE_CALENDAR_ID: str = os.getenv(
            "GOOGLE_CALENDAR_ID",
            str(_get_nested(self._yaml, ["google_calendar", "calendar_id"], "primary")),
        )
        self.GOOGLE_CALENDAR_SCOPES: list[str] = _env_csv(
            "GOOGLE_CALENDAR_SCOPES",
            _to_csv_list(
                _get_nested(
                    self._yaml,
                    ["google_calendar", "scopes"],
                    ["https://www.googleapis.com/auth/calendar"],
                ),
                ["https://www.googleapis.com/auth/calendar"],
            ),
        )

        # Scheduler
        self.SCHEDULER_TIMEZONE: str = os.getenv(
            "SCHEDULER_TIMEZONE",
            str(_get_nested(self._yaml, ["scheduler", "timezone"], "UTC")),
        )
        self.SCHEDULER_WORK_START_HOUR: int = _env_int(
            "SCHEDULER_WORK_START_HOUR",
            _to_int(_get_nested(self._yaml, ["scheduler", "work_start_hour"], 9), 9),
        )
        self.SCHEDULER_WORK_END_HOUR: int = _env_int(
            "SCHEDULER_WORK_END_HOUR",
            _to_int(_get_nested(self._yaml, ["scheduler", "work_end_hour"], 18), 18),
        )
        self.SCHEDULER_MIN_SLOT_MINUTES: int = _env_int(
            "SCHEDULER_MIN_SLOT_MINUTES",
            _to_int(_get_nested(self._yaml, ["scheduler", "min_slot_minutes"], 30), 30),
        )
        self.SCHEDULER_DEFAULT_DURATION_MINUTES: int = _env_int(
            "SCHEDULER_DEFAULT_DURATION_MINUTES",
            _to_int(_get_nested(self._yaml, ["scheduler", "default_duration_minutes"], 30), 30),
        )
        self.SCHEDULER_MAX_ALTERNATIVE_DAYS: int = _env_int(
            "SCHEDULER_MAX_ALTERNATIVE_DAYS",
            _to_int(_get_nested(self._yaml, ["scheduler", "max_alternative_days"], 7), 7),
        )
        self.SCHEDULER_MAX_ALTERNATIVES: int = _env_int(
            "SCHEDULER_MAX_ALTERNATIVES",
            _to_int(_get_nested(self._yaml, ["scheduler", "max_alternatives"], 3), 3),
        )
        self.SCHEDULER_EVENT_FETCH_MAX_RESULTS: int = _env_int(
            "SCHEDULER_EVENT_FETCH_MAX_RESULTS",
            _to_int(_get_nested(self._yaml, ["scheduler", "event_fetch_max_results"], 50), 50),
        )
        self.SCHEDULER_PARSER_MODEL: str = os.getenv(
            "SCHEDULER_PARSER_MODEL",
            str(_get_nested(self._yaml, ["scheduler", "parser_model"], "gpt-4o-mini")),
        )


settings = Settings()