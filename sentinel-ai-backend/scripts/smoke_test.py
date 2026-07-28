from app.core.config import get_settings

s = get_settings()
print(f"Settings OK: app={s.APP_NAME!r} env={s.APP_ENV!r} version={s.VERSION!r}")

from app.main import app

print(f"App OK: {app.title!r}")
