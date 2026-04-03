"""
account_ui_profiler.py — Détection automatique du profil UI Facebook par compte

Problème résolu :
    Facebook affiche des aria-label et textes différents selon :
    - La langue du compte (fr, en, ar, tr, es, ru, pt...)
    - L'ancienneté du compte (vieux comptes = interface "legacy", nouveaux = "modern")
    - Les tests A/B Facebook (variante "alt" pour certains comptes)

    Ce module détecte automatiquement le profil UI dès que le compte
    se connecte, puis stocke le résultat en base pour ne pas refaire
    la détection à chaque run.

Usage :
    from libs.account_ui_profiler import AccountUIProfiler

    profiler = AccountUIProfiler(page, db, account_name="robot1")
    profile  = profiler.detect()
    # → {"lang": "fr", "variant": "modern", "detected_at": "..."}

Langues supportées :
    fr, en, ar, tr, es, ru, pt, de, it, nl, pl, id, hi, bn
"""

import re
import time
import json
from datetime import datetime
from typing import Optional

try:
    from libs.log_emitter import emit
    from libs.database import get_database
except ImportError:
    from log_emitter import emit
    from database import get_database


# ─── Signatures de détection de langue ────────────────────────────────────────
# Pour chaque langue : liste de textes/aria-label caractéristiques présents
# dans l'interface Facebook (barre de navigation, boutons, etc.)

LANG_SIGNATURES: dict[str, list[str]] = {
    "fr": [
        "Qu'avez-vous en tête",
        "Écrire quelque chose",
        "Publier",
        "Fil d'actualité",
        "Amis",
        "Accueil",
        "Groupes",
        "Quoi de neuf",
    ],
    "en": [
        "What's on your mind",
        "Write something",
        "Post",
        "News Feed",
        "Friends",
        "Home",
        "Groups",
        "What's new",
    ],
    "ar": [
        "ما الذي تفكر فيه",
        "اكتب شيئاً",
        "نشر",
        "الرئيسية",
        "الأصدقاء",
        "المجموعات",
        "ما الجديد",
    ],
    "tr": [
        "Ne düşünüyorsun",
        "Bir şeyler yaz",
        "Paylaş",
        "Ana Sayfa",
        "Arkadaşlar",
        "Gruplar",
        "Neler oluyor",
    ],
    "es": [
        "¿En qué estás pensando",
        "Escribe algo",
        "Publicar",
        "Inicio",
        "Amigos",
        "Grupos",
        "Novedades",
    ],
    "ru": [
        "О чём вы думаете",
        "Написать что-нибудь",
        "Опубликовать",
        "Главная",
        "Друзья",
        "Группы",
    ],
    "pt": [
        "No que você está pensando",
        "Escreva algo",
        "Publicar",
        "Início",
        "Amigos",
        "Grupos",
    ],
    "de": [
        "Was machst du gerade",
        "Schreib etwas",
        "Beitrag",
        "Startseite",
        "Freunde",
        "Gruppen",
    ],
    "it": [
        "A cosa stai pensando",
        "Scrivi qualcosa",
        "Pubblica",
        "Home",
        "Amici",
        "Gruppi",
    ],
    "nl": [
        "Waar denk je aan",
        "Schrijf iets",
        "Plaatsen",
        "Startpagina",
        "Vrienden",
        "Groepen",
    ],
    "pl": [
        "Co masz na myśli",
        "Napisz coś",
        "Udostępnij",
        "Aktualności",
        "Znajomi",
        "Grupy",
    ],
    "id": [
        "Apa yang Anda pikirkan",
        "Tulis sesuatu",
        "Posting",
        "Beranda",
        "Teman",
        "Grup",
    ],
    "hi": [
        "आप क्या सोच रहे हैं",
        "कुछ लिखें",
        "पोस्ट करें",
        "होम",
        "दोस्त",
        "ग्रुप",
    ],
    "bn": [
        "আপনি কী ভাবছেন",
        "কিছু লিখুন",
        "পোস্ট করুন",
        "হোম",
        "বন্ধু",
        "গ্রুপ",
    ],
}

# ─── Signatures de détection de variante UI ───────────────────────────────────
# "legacy"  : vieux comptes FB (interface pré-2022, structure DOM différente)
# "modern"  : interface standard 2022+
# "alt"     : variante A/B test (layouts alternatifs déployés par FB)
# "mobile"  : interface responsive / PWA mobile

VARIANT_SIGNATURES: dict[str, list[str]] = {
    "legacy": [
        # Ancien composer FB
        "[data-testid='status-attachment-mentions-input']",
        "#composerInput",
        "textarea[name='xhpc_message']",
        ".UFIInputContainer",
        # Ancienne nav
        "#pagelet_composer",
        "div.UFICommentContentBlock",
    ],
    "modern": [
        # Nouveau composer Lexical
        "div[data-lexical-editor='true']",
        "div[data-contents='true']",
        # Nouvelle nav
        "div[role='banner'] nav",
        "div[aria-label='Facebook'][role='main']",
    ],
    "alt": [
        # Variante avec boutons de composition différents
        "div[data-pagelet='FeedComposer']",
        "[data-testid='react-composer-post-button']",
        "div[aria-label*='composer']",
    ],
}


class UIProfile:
    """Profil UI détecté pour un compte Facebook."""

    def __init__(
        self,
        lang: str = "en",
        variant: str = "modern",
        confidence: int = 0,
        detected_at: str = None,
        source: str = "auto",
    ):
        self.lang        = lang
        self.variant     = variant
        self.confidence  = confidence        # 0-100
        self.detected_at = detected_at or datetime.now().isoformat()
        self.source      = source            # "auto" | "cache" | "forced"

    def is_stale(self, max_age_hours: int = 48) -> bool:
        """Retourne True si le profil a plus de max_age_hours heures."""
        try:
            dt = datetime.fromisoformat(self.detected_at)
            age_h = (datetime.now() - dt).total_seconds() / 3600
            return age_h > max_age_hours
        except Exception:
            return True

    def to_dict(self) -> dict:
        return {
            "lang":        self.lang,
            "variant":     self.variant,
            "confidence":  self.confidence,
            "detected_at": self.detected_at,
            "source":      self.source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UIProfile":
        return cls(
            lang        = d.get("lang", "en"),
            variant     = d.get("variant", "modern"),
            confidence  = d.get("confidence", 0),
            detected_at = d.get("detected_at"),
            source      = d.get("source", "cache"),
        )

    def __repr__(self):
        return f"UIProfile(lang={self.lang}, variant={self.variant}, conf={self.confidence}%)"


class AccountUIProfiler:
    """
    Détecte automatiquement le profil UI Facebook d'un compte.

    Stratégie de détection (4 niveaux) :
    1. Cache DB (si < 48h) → instantané, 0 requête réseau
    2. Analyse du DOM de la page actuelle (lang HTML + aria-labels)
    3. Navigation légère sur /home pour collecter plus de signaux
    4. Fallback sur profil par défaut (en/modern)
    """

    def __init__(self, page, db=None, account_name: str = ""):
        self.page         = page
        self.db           = db or get_database()
        self.account_name = account_name

    # ── API publique ───────────────────────────────────────────────────────

    def detect(self, force_refresh: bool = False) -> UIProfile:
        """
        Détecte (ou charge depuis le cache) le profil UI du compte.

        Args:
            force_refresh: ignore le cache et re-détecte

        Returns:
            UIProfile
        """
        # 1. Cache DB
        if not force_refresh:
            cached = self._load_from_db()
            if cached and not cached.is_stale():
                emit("DEBUG", "UI_PROFILE_CACHE_HIT",
                     account=self.account_name,
                     lang=cached.lang,
                     variant=cached.variant)
                return cached

        # 2. Détection DOM
        profile = self._detect_from_dom()

        # 3. Stocker en base
        self._save_to_db(profile)

        emit("INFO", "UI_PROFILE_DETECTED",
             account=self.account_name,
             lang=profile.lang,
             variant=profile.variant,
             confidence=profile.confidence)

        return profile

    # ── Détection DOM ──────────────────────────────────────────────────────

    def _detect_from_dom(self) -> UIProfile:
        """Analyse le DOM pour détecter langue et variante."""
        try:
            # A. Langue via attribut lang du HTML
            lang_from_html = self._detect_lang_from_html_attr()

            # B. Langue via analyse des aria-labels / textes visible
            lang_from_text, lang_confidence = self._detect_lang_from_text()

            # C. Fusion : html_attr > text analysis
            if lang_from_html and lang_from_html in LANG_SIGNATURES:
                final_lang = lang_from_html
                confidence = max(lang_confidence, 80)
            elif lang_from_text:
                final_lang = lang_from_text
                confidence = lang_confidence
            else:
                final_lang = "en"
                confidence = 10

            # D. Navigation /home si confiance insuffisante (< 50%)
            #    Si la page actuelle est un groupe/profil sans navbar complète,
            #    on charge /home pour obtenir plus de signaux textuels.
            if confidence < 50:
                try:
                    self.page.goto(
                        "https://www.facebook.com/?sk=h_nor",
                        wait_until="domcontentloaded",
                        timeout=15000,
                    )
                    self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                    lang_from_html2 = self._detect_lang_from_html_attr()
                    lang_from_text2, lang_confidence2 = self._detect_lang_from_text()
                    if lang_from_html2 and lang_from_html2 in LANG_SIGNATURES:
                        final_lang = lang_from_html2
                        confidence = max(lang_confidence2, 80)
                    elif lang_from_text2 and lang_confidence2 > confidence:
                        final_lang = lang_from_text2
                        confidence = lang_confidence2
                    emit(
                        "DEBUG",
                        "UI_PROFILE_NAVIGATED_HOME",
                        account=self.account_name,
                        new_lang=final_lang,
                        new_confidence=confidence,
                    )
                except Exception as _nav_err:
                    emit(
                        "DEBUG",
                        "UI_PROFILE_HOME_NAV_FAILED",
                        account=self.account_name,
                        error=str(_nav_err),
                    )

            # E. Détection variante
            variant = self._detect_variant()

            return UIProfile(
                lang       = final_lang,
                variant    = variant,
                confidence = confidence,
                source     = "auto",
            )

        except Exception as e:
            emit("WARN", "UI_PROFILE_DETECT_ERROR",
                 account=self.account_name, error=str(e))
            return UIProfile(lang="en", variant="modern", confidence=0, source="fallback")

    def _detect_lang_from_html_attr(self) -> Optional[str]:
        """Lit l'attribut lang de la balise <html>."""
        try:
            lang_attr = self.page.evaluate("document.documentElement.lang || ''")
            if lang_attr:
                # "fr-FR" → "fr", "ar-SA" → "ar", etc.
                lang_code = lang_attr.split("-")[0].lower()
                if lang_code in LANG_SIGNATURES:
                    return lang_code
                # Mapping étendu
                mapping = {
                    "zh": "zh", "ja": "ja", "ko": "ko",
                    "fa": "ar",  # persan → fallback arabe (RTL)
                    "ur": "ar",  # ourdou → fallback arabe (RTL)
                }
                return mapping.get(lang_code)
        except Exception:
            pass
        return None

    def _detect_lang_from_text(self) -> tuple[str, int]:
        """
        Analyse les aria-labels et textes visibles pour identifier la langue.
        Retourne (lang_code, confidence_score).
        """
        try:
            # Collecter les textes accessibles de la page
            page_text = self.page.evaluate("""
                () => {
                    const texts = [];
                    // aria-labels
                    document.querySelectorAll('[aria-label]').forEach(el => {
                        const v = el.getAttribute('aria-label');
                        if (v && v.length > 2) texts.push(v);
                    });
                    // Textes des boutons principaux
                    document.querySelectorAll(
                        "div[role='button'], button, [role='navigation'] span"
                    ).forEach(el => {
                        const t = el.innerText || el.textContent || '';
                        if (t.trim().length > 2) texts.push(t.trim());
                    });
                    return texts.join(' ||| ');
                }
            """)
        except Exception:
            return "en", 0

        if not page_text:
            return "en", 0

        scores: dict[str, int] = {}
        for lang, signatures in LANG_SIGNATURES.items():
            score = 0
            for sig in signatures:
                if sig in page_text:
                    score += 1
            if score > 0:
                scores[lang] = score

        if not scores:
            return "en", 10

        best_lang = max(scores, key=lambda k: scores[k])
        best_score = scores[best_lang]
        total_sigs = len(LANG_SIGNATURES[best_lang])
        confidence = min(100, int(best_score * 100 / max(total_sigs, 1)))

        return best_lang, confidence

    def _detect_variant(self) -> str:
        """
        Détecte la variante de l'interface Facebook.
        Priorité : legacy > alt > modern
        """
        try:
            for variant, selectors in VARIANT_SIGNATURES.items():
                for sel in selectors:
                    try:
                        el = self.page.query_selector(sel)
                        if el:
                            return variant
                    except Exception:
                        continue
        except Exception:
            pass
        return "modern"

    # ── Persistance DB ─────────────────────────────────────────────────────

    def _load_from_db(self) -> Optional[UIProfile]:
        """Charge le profil UI depuis la base de données."""
        try:
            account = self.db.get_account(self.account_name)
            if not account:
                return None

            ui_lang    = account.get("ui_lang") if hasattr(account, "get") else None
            ui_variant = account.get("ui_variant") if hasattr(account, "get") else None
            ui_detected_at = account.get("ui_detected_at") if hasattr(account, "get") else None

            if ui_lang and ui_variant:
                return UIProfile(
                    lang        = ui_lang,
                    variant     = ui_variant,
                    confidence  = account.get("ui_confidence", 0) if hasattr(account, "get") else 0,
                    detected_at = ui_detected_at,
                    source      = "cache",
                )
        except Exception as e:
            emit("DEBUG", "UI_PROFILE_DB_LOAD_ERROR", error=str(e))
        return None

    def _save_to_db(self, profile: UIProfile) -> None:
        """Sauvegarde le profil UI en base de données."""
        try:
            self.db.update_account_ui_profile(
                self.account_name,
                lang       = profile.lang,
                variant    = profile.variant,
                confidence = profile.confidence,
            )
        except Exception as e:
            emit("WARN", "UI_PROFILE_DB_SAVE_ERROR",
                 account=self.account_name, error=str(e))
