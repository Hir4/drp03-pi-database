from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuração do app que concentra o domínio operacional da FCN TI."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Operações FCN TI"
