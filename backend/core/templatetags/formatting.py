"""Filtros de formatação no padrão brasileiro, usados em todas as telas.

Garante que dinheiro, percentuais e horas apareçam iguais no dashboard, em
Projetos, em Análises e no relatório em PDF:

- ``{{ valor|brl }}``   -> ``R$ 90.000,00``
- ``{{ valor|pct }}``   -> ``40,0%``
- ``{{ valor|hours }}`` -> ``12,5h``
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template

register = template.Library()


def _to_decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def format_number(value, decimals: int = 2) -> str:
    """Formata com separador de milhar ``.`` e decimal ``,``."""
    number = _to_decimal(value)
    if number is None:
        return "—"
    quantizer = Decimal(1).scaleb(-decimals)
    number = number.quantize(quantizer, rounding=ROUND_HALF_UP)
    sign = "-" if number < 0 else ""
    integer, _, fraction = f"{abs(number):.{decimals}f}".partition(".")
    grouped = f"{int(integer):,}".replace(",", ".")
    return f"{sign}{grouped},{fraction}" if decimals else f"{sign}{grouped}"


@register.filter
def brl(value) -> str:
    """Valor monetário em reais: ``R$ 1.234,56``."""
    formatted = format_number(value, 2)
    return formatted if formatted == "—" else f"R$ {formatted}"


@register.filter
def pct(value, decimals: int = 1) -> str:
    """Percentual com uma casa decimal: ``40,0%``."""
    formatted = format_number(value, int(decimals))
    return formatted if formatted == "—" else f"{formatted}%"


@register.filter
def hours(value, decimals: int = 1) -> str:
    """Horas com uma casa decimal: ``12,5h``."""
    formatted = format_number(value, int(decimals))
    return formatted if formatted == "—" else f"{formatted}h"


HEALTH_BADGES = {
    "Saudável": ("ok", "✓"),
    "No ritmo": ("ok", "✓"),
    "Atenção": ("warning", "!"),
    "Crítico": ("high", "✕"),
    "Em risco": ("high", "✕"),
}


@register.inclusion_tag("core/components/status_badge.html")
def status_badge(label: str, hint: str = ""):
    """Selo de status com ícone + texto (não depende só da cor, WCAG 1.4.1)."""
    level, icon = HEALTH_BADGES.get(label, ("neutral", "•"))
    return {"label": label, "level": level, "icon": icon, "hint": hint}
