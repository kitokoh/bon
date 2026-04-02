#!/usr/bin/env python3
"""
Génère le rapport PDF BON v11 (texte en français).
Exécution : python tools/gen_rapport_pdf.py
Sortie   : Rapport_BON_v11.pdf (racine du dépôt)
"""
from __future__ import annotations

import pathlib
import sys
from datetime import date

try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
except ImportError:
    print("Installez fpdf2 : pip install fpdf2", file=sys.stderr)
    sys.exit(1)

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "Rapport_BON_v11.pdf"


def _font_regular() -> pathlib.Path:
    win = pathlib.Path(r"C:\Windows\Fonts\arial.ttf")
    if win.exists():
        return win
    for p in (
        pathlib.Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        pathlib.Path("/Library/Fonts/Arial.ttf"),
    ):
        if p.exists():
            return p
    raise FileNotFoundError(
        "Police TrueType introuvable (Arial/DejaVu). "
        "Sous Windows : vérifiez C:\\Windows\\Fonts\\arial.ttf"
    )


def _font_bold() -> pathlib.Path:
    win = pathlib.Path(r"C:\Windows\Fonts\arialbd.ttf")
    if win.exists():
        return win
    for p in (
        pathlib.Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        pathlib.Path("/Library/Fonts/Arial Bold.ttf"),
    ):
        if p.exists():
            return p
    return _font_regular()


class Rapport(FPDF):
    def __init__(self):
        super().__init__(format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        reg = str(_font_regular())
        bld = str(_font_bold())
        self.add_font("BonSans", "", reg)
        self.add_font("BonSans", "B", bld)
        self.set_title("Rapport technique — BON v11")

    def header(self):
        self.set_font("BonSans", "B", 11)
        self.cell(
            0, 8, "BON — Facebook Groups Publisher",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        self.set_font("BonSans", "", 9)
        self.set_text_color(80, 80, 80)
        self.cell(
            0, 6, f"Rapport de synthèse — version 11 — {date.today().isoformat()}",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_font("BonSans", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)

    def section(self, title: str):
        self.ln(3)
        self.set_font("BonSans", "B", 12)
        self.multi_cell(self.epw, 7, title)
        self.ln(1)

    def body(self, text: str):
        self.set_font("BonSans", "", 10)
        self.multi_cell(self.epw, 5.5, text)
        self.ln(1)

    def bullet_list(self, items: list[str]):
        self.set_font("BonSans", "", 10)
        for line in items:
            self.multi_cell(self.epw, 5.5, f"  \u2022 {line}")
        self.ln(2)


def build() -> None:
    pdf = Rapport()
    pdf.add_page()

    pdf.section("1. Objet du document")
    pdf.body(
        "Ce document présente l'état du projet BON (module de publication automatisée "
        "dans des groupes Facebook), l'architecture technique retenue, les apports de la "
        "version 11 par rapport aux versions précédentes, et les perspectives identifiées "
        "dans la feuille de route. Il s'adresse à un public technique ou décisionnel "
        "devant évaluer la maintenabilité, la sécurité opérationnelle et les risques liés "
        "à l'automatisation sur des plateformes tierces."
    )

    pdf.section("2. Contexte et positionnement")
    pdf.body(
        "BON s'exécute en autonome (venv Python, Playwright/Chromium). Chaque « robot » "
        "correspond à une instance nommée liée à un compte Facebook et à un fichier de "
        "session Playwright. La configuration métier (groupes, campagnes, variantes de "
        "texte, médias) est stockée principalement dans une base SQLite ; les sélecteurs "
        "DOM sont externalisés en JSON pour s'adapter aux changements fréquents de "
        "l'interface Facebook."
    )

    pdf.section("3. Architecture (synthèse)")
    pdf.bullet_list(
        [
            "Point d'entrée CLI : __main__.py (commandes robot, post, migrate, dashboard, etc.).",
            "Couche navigateur : libs/playwright_engine.py, profil stealth (libs/stealth_profile.py).",
            "Métier : libs/scraper.py, libs/social_actions.py, automation/ (anti-blocage, santé sélecteurs).",
            "Persistance : libs/database.py (SQLite, modèle Robot, publications, circuit breaker, files DM).",
            "Notifications : Telegram via libs/notifier.py (configuration par robot).",
        ]
    )

    pdf.section("4. Évolutions majeures — version 11")
    pdf.body(
        "La v11 renforce l'exploitabilité en production et corrige des écarts identifiés "
        "lors d'audits (URL CDN fictive, proxy peu visible en CLI, besoin d'export et "
        "d'API de supervision)."
    )
    pdf.bullet_list(
        [
            "CDN sélecteurs : activation explicite (BON_USE_CDN), URL configurable ; plus de dépôt GitHub imposé par défaut.",
            "Proxy : création et configuration robot via CLI ; validation optionnelle du proxy avant publication.",
            "Export CSV et XLSX des publications (openpyxl) ; pagination SQL ; export via API.",
            "Intégration 2captcha (libs/captcha_solver.py), journal captcha_solve_log, auto si BON_AUTO_SOLVE_CAPTCHA=1.",
            "Planificateur : APScheduler, table scheduler_jobs, commande schedule daemon.",
            "API REST Flask : BON_API_TOKEN ; routes /v1/* et alias /api/v1/* (campagnes, groupes, erreurs, export).",
            "Rotation cross-robots : BON_CROSS_ROBOT_VARIANT_EXCLUSION ; tests test_v10 / test_v11 ; plan v12 : docs/PLAN_ACTION_V12.md.",
        ]
    )

    pdf.section("5. Variables d'environnement et sécurité")
    pdf.bullet_list(
        [
            "BON_USE_CDN / BON_SELECTORS_CDN_URL / BON_SELECTORS_CACHE_TTL_S — mise à jour des sélecteurs.",
            "BON_API_TOKEN — obligatoire pour démarrer l'API REST.",
            "BON_2CAPTCHA_KEY — résolution CAPTCHA via service tiers.",
            "BON_AUTO_SOLVE_CAPTCHA — active la résolution automatique dans le navigateur (reCAPTCHA / hCaptcha).",
            "BON_CROSS_ROBOT_VARIANT_EXCLUSION — évite la réutilisation d'un même variant sur un groupe par plusieurs robots.",
            "Les fichiers de session Playwright et mots de passe proxy ne doivent pas être versionnés (.gitignore).",
        ]
    )

    pdf.section("6. Limites et conformité")
    pdf.body(
        "L'automatisation sur Facebook peut être interdite ou limitée par les conditions "
        "d'utilisation de la plateforme. Ce logiciel est fourni à des fins techniques ; "
        "l'exploitant reste responsable du respect du droit applicable et des règles du "
        "réseau social. Les mécanismes anti-détection et de fréquence visent à réduire "
        "les risques techniques ; ils ne constituent pas une garantie contre les sanctions "
        "de plateforme."
    )

    pdf.section("7. Perspectives (feuille de route)")
    pdf.bullet_list(
        [
            "Tests E2E sur DOM synthétique (robustesse des flux post / session expirée).",
            "Dashboard web enrichi (métriques, graphes, états circuit breaker).",
            "Adaptateur base de données optionnel (PostgreSQL) pour déploiements multi-instance.",
        ]
    )

    pdf.section("8. Conclusion")
    pdf.body(
        "La version 11 consolide BON autour d'une base SQLite déjà mature (v8–v10), en "
        "ajoutant les briques attendues pour une exploitation encadrée : proxy, CDN "
        "sélecteurs explicite, export, planification, API supervisée et traçabilité CAPTCHA. "
        "La priorité suivante pour la qualité logicielle reste l'automatisation des tests "
        "de bout en bout sur le navigateur, complémentaire aux tests unitaires actuels."
    )

    pdf.output(str(OUT))


if __name__ == "__main__":
    build()
    print(f"Écrit : {OUT}")
