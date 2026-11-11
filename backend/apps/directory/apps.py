from django.apps import AppConfig


class DirectoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.directory"
    label = "directory"

    def ready(self):
        from apps.directory import signals  # noqa: F401
