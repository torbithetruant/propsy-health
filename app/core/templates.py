from fastapi.templating import Jinja2Templates
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parents[1] / "templates"
# print(f"📂 Loading templates from: {TEMPLATES_DIR}")

# Ensure the templates directory exists
if not TEMPLATES_DIR.exists():
    raise FileNotFoundError(f"Templates directory not found: {TEMPLATES_DIR}")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def format_datetime(value, format="%d/%m/%Y %H:%M"):
    if value:
        return value.strftime(format)
    return ""

templates.env.filters["datetime"] = format_datetime