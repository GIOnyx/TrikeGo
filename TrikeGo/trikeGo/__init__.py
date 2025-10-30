try:
	from .celery import app as celery_app
except Exception:
	# Celery may not be installed in all environments; fail silently.
	celery_app = None

# Expose celery app as a module-level symbol for `celery -A trikeGo`
__all__ = ('celery_app',)
