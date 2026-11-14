"""Testes dos filtros de formatação pt-BR e dos indicadores de risco compartilhados."""

from __future__ import annotations

from decimal import Decimal

from django.template import Context, Template
from django.test import SimpleTestCase

from core.services import delivery_risk
from core.templatetags.formatting import brl, format_number, hours, pct


class FormattingFilterTests(SimpleTestCase):
    def test_brl_uses_brazilian_separators(self) -> None:
        self.assertEqual(brl(Decimal("90000")), "R$ 90.000,00")
        self.assertEqual(brl(Decimal("1234.5")), "R$ 1.234,50")

    def test_pct_and_hours(self) -> None:
        self.assertEqual(pct(Decimal("72.456")), "72,5%")
        self.assertEqual(pct(Decimal("72.456"), 0), "72%")
        self.assertEqual(hours(Decimal("7.5")), "7,5h")

    def test_invalid_values_do_not_break_the_page(self) -> None:
        self.assertEqual(format_number(None), "—")
        self.assertEqual(brl("abc"), "—")

    def test_status_badge_has_icon_and_label(self) -> None:
        html = Template("{% load formatting %}{% status_badge 'Em risco' %}").render(Context())
        self.assertIn("status-high", html)
        self.assertIn('aria-hidden="true"', html)
        self.assertIn("Em risco", html)


class DeliveryRiskTests(SimpleTestCase):
    def test_thresholds(self) -> None:
        self.assertEqual(delivery_risk(Decimal("50"), Decimal("45"))["risk_level"], "ok")
        self.assertEqual(delivery_risk(Decimal("60"), Decimal("45"))["risk_level"], "warning")
        self.assertEqual(delivery_risk(Decimal("80"), Decimal("45"))["risk_label"], "Em risco")
