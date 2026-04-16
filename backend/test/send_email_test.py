import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_openai_key_from_dotenv(project_root: Path) -> None:
    if os.environ.get("OPENAI_API_KEY"):
        return

    env_path = project_root / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key == "OPENAI_API_KEY" and value:
            os.environ["OPENAI_API_KEY"] = value
            return


_load_openai_key_from_dotenv(PROJECT_ROOT)

from backend.agents.email_agent import EmailAgent
from backend.services.email_service import send_email_service


# 1. your email (already fetched)
email = {
    "sender": "sikandarnust1140@gmail.com",
    "subject": "Project Update",
    "body_clean": "Can you send me the latest report by today?"
}

# 2. create agent
agent = EmailAgent()

# 3. generate reply
reply = agent.generate_reply(email)

# 4. format for sending
payload = agent.send_reply(email, reply)

# 5. send email
result = send_email_service(
    to=payload["to"],
    subject=payload["subject"],
    body=payload["body"],
)

print(result)