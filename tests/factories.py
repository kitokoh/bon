"""
factories.py v9 — Factories et Seeders pour les tests BON

Usage :
    from tests.factories import RobotFactory, CampaignFactory, MediaFactory, Seeder
    db = BONDatabase(":memory:")
    robot = RobotFactory.create(db, "robot1")
    camp  = CampaignFactory.create(db, "farmoos")
    Seeder.seed_all(db)   # jeu de données complet pour dev/tests
"""
import pathlib
import random
import string
from datetime import datetime, timedelta
from typing import Optional

try:
    from libs.database import BONDatabase
except ImportError:
    from database import BONDatabase


def _rand_str(n=8):
    return "".join(random.choices(string.ascii_lowercase, k=n))


# ═══════════════════════════════════════════════════════════════════
# AccountFactory
# ═══════════════════════════════════════════════════════════════════

class AccountFactory:
    @staticmethod
    def create(db: BONDatabase, name: str = None, **kwargs) -> dict:
        name = name or f"compte_{_rand_str(4)}"
        db.ensure_account_exists(name)
        row = db.get_account(name)
        return dict(row)

    @staticmethod
    def create_batch(db: BONDatabase, count: int = 3) -> list:
        return [AccountFactory.create(db, f"compte{i+1}") for i in range(count)]


# ═══════════════════════════════════════════════════════════════════
# RobotFactory
# ═══════════════════════════════════════════════════════════════════

class RobotFactory:
    @staticmethod
    def create(db: BONDatabase, robot_name: str = None,
               account_name: str = None, **kwargs) -> dict:
        robot_name   = robot_name   or f"robot{random.randint(1,99)}"
        account_name = account_name or f"compte_{robot_name}"
        storage_path = kwargs.get("storage_state_path",
                                   f"/tmp/test_{robot_name}_state.json")
        config = {
            "max_groups_per_run":      kwargs.get("max_groups_per_run", 5),
            "max_groups_per_hour":     kwargs.get("max_groups_per_hour", 3),
            "delay_between_groups":    [30, 60],
            "max_runs_per_day":        kwargs.get("max_runs_per_day", 2),
            "cooldown_between_runs_s": kwargs.get("cooldown_between_runs_s", 3600),
            "locale":                  kwargs.get("locale", "fr-FR"),
            "timezone_id":             kwargs.get("timezone_id", "Europe/Paris"),
            "platform":                kwargs.get("platform", "windows"),
        }
        db.upsert_robot(robot_name, account_name, storage_path, config)
        return db.get_robot(robot_name)

    @staticmethod
    def create_batch(db: BONDatabase, count: int = 3) -> list:
        return [
            RobotFactory.create(db, f"robot{i+1}", f"compte{i+1}")
            for i in range(count)
        ]


# ═══════════════════════════════════════════════════════════════════
# GroupFactory
# ═══════════════════════════════════════════════════════════════════

class GroupFactory:
    CATEGORIES = ["agriculture", "technology", "automotive", "home", "food"]
    LANGUAGES  = ["fr", "en", "ar"]

    @staticmethod
    def create(db: BONDatabase, url: str = None, **kwargs) -> dict:
        key  = _rand_str(6)
        url  = url or f"https://www.facebook.com/groups/{key}/"
        name = kwargs.get("name", f"Groupe {key.upper()}")
        cat  = kwargs.get("category", random.choice(GroupFactory.CATEGORIES))
        lang = kwargs.get("language", random.choice(GroupFactory.LANGUAGES))
        db.add_group(url=url, name=name, category=cat, language=lang)
        return db.get_group_by_url(url)

    @staticmethod
    def create_batch(db: BONDatabase, count: int = 6) -> list:
        return [GroupFactory.create(db) for _ in range(count)]

    @staticmethod
    def assign_to_robot(db: BONDatabase, robot_name: str,
                         groups: list) -> None:
        for g in groups:
            db.assign_group_to_robot(robot_name, g["url"])


# ═══════════════════════════════════════════════════════════════════
# CampaignFactory
# ═══════════════════════════════════════════════════════════════════

class CampaignFactory:
    SAMPLE_TEXTS_FR = [
        "Découvrez nos produits innovants ! Qualité garantie.",
        "Offre spéciale cette semaine seulement. Ne ratez pas !",
        "Solutions professionnelles pour votre activité.",
        "Rejoignez des milliers de clients satisfaits !",
    ]
    SAMPLE_TEXTS_EN = [
        "Discover our innovative products! Quality guaranteed.",
        "Special offer this week only. Don't miss out!",
    ]
    SAMPLE_TEXTS_AR = [
        "اكتشف منتجاتنا المبتكرة! جودة مضمونة.",
        "عرض خاص هذا الأسبوع فقط. لا تفوتوه!",
    ]
    BG_COLORS = [None, None, "blue", "green", "red", None]  # None = majoritaire

    @staticmethod
    def create(db: BONDatabase, name: str = None,
               variant_count: int = 3, **kwargs) -> dict:
        name = name or f"campagne_{_rand_str(4)}"
        cid  = db.upsert_campaign(
            name        = name,
            description = kwargs.get("description", f"Campagne {name}"),
            language    = kwargs.get("language", "fr"),
            active      = True,
        )
        for i in range(variant_count):
            db.upsert_variant(
                campaign_id = cid,
                variant_key = f"v{i+1}",
                text_fr     = random.choice(CampaignFactory.SAMPLE_TEXTS_FR),
                text_en     = random.choice(CampaignFactory.SAMPLE_TEXTS_EN),
                text_ar     = random.choice(CampaignFactory.SAMPLE_TEXTS_AR),
                cta         = random.choice(["En savoir plus", "Découvrir", "Commander", ""]),
                weight      = random.randint(1, 5),
                bg_color    = random.choice(CampaignFactory.BG_COLORS),
                post_type   = random.choice(["text_image", "text_image", "text_only"]),
            )
        return db.get_campaign_by_name(name)

    @staticmethod
    def create_batch(db: BONDatabase, count: int = 3) -> list:
        names = ["farmoos", "doorika", "kitokoh", "novatech", "kps"]
        return [
            CampaignFactory.create(db, name=names[i] if i < len(names) else None)
            for i in range(count)
        ]

    @staticmethod
    def assign_to_robot(db: BONDatabase, robot_name: str,
                         campaigns: list) -> None:
        for c in campaigns:
            db.assign_campaign_to_robot(robot_name, c["name"])


# ═══════════════════════════════════════════════════════════════════
# MediaFactory
# ═══════════════════════════════════════════════════════════════════

class MediaFactory:
    SAMPLE_CAPTIONS = [
        "Image de présentation du produit.",
        "Visuel promotionnel haute qualité.",
        "Photo officielle de la campagne.",
        None, None,  # Sans description
    ]
    SAMPLE_CAPTCHAS = [
        "Code promo : PROMO10",
        "Réf : REF-2025",
        None, None, None,  # Captcha optionnel (majoritairement absent)
    ]

    @staticmethod
    def create(db: BONDatabase, file_path: str = None,
               campaign_id: int = None, **kwargs) -> dict:
        fname = kwargs.get("file_name", f"media_{_rand_str(6)}.jpg")
        fpath = file_path or f"/tmp/media/{fname}"
        mid   = db.add_media_asset(
            file_path    = fpath,
            file_name    = fname,
            campaign_id  = campaign_id,
            captcha_text = kwargs.get("captcha_text",
                                       random.choice(MediaFactory.SAMPLE_CAPTCHAS)),
            description  = kwargs.get("description",
                                       random.choice(MediaFactory.SAMPLE_CAPTIONS)),
        )
        row = db._query_one("SELECT * FROM media_assets WHERE id=?", (mid,))
        return dict(row) if row else {}

    @staticmethod
    def create_batch(db: BONDatabase, count: int = 5,
                      campaign_id: int = None) -> list:
        return [MediaFactory.create(db, campaign_id=campaign_id) for _ in range(count)]

    @staticmethod
    def assign_to_robot(db: BONDatabase, robot_name: str,
                         medias: list) -> None:
        for m in medias:
            db.assign_media_to_robot(robot_name, m["id"])


# ═══════════════════════════════════════════════════════════════════
# CommentFactory
# ═══════════════════════════════════════════════════════════════════

class CommentFactory:
    SAMPLE_COMMENTS = [
        "Super post, merci !",
        "Très intéressant 👍",
        "J'adore ce contenu !",
        "Merci pour le partage.",
        "Excellent !",
        "Continuez comme ça !",
        "Belle publication.",
        "Très utile, merci !",
        "Parfait !",
        "Top !",
    ]

    @staticmethod
    def create(db: BONDatabase, text: str = None,
               robot_name: str = None) -> int:
        text = text or random.choice(CommentFactory.SAMPLE_COMMENTS)
        return db.add_comment(text, robot_name)

    @staticmethod
    def create_batch(db: BONDatabase, count: int = 10,
                      robot_name: str = None) -> list:
        created = []
        for text in random.sample(CommentFactory.SAMPLE_COMMENTS,
                                    min(count, len(CommentFactory.SAMPLE_COMMENTS))):
            cid = db.add_comment(text, robot_name)
            created.append(cid)
        return created


# ═══════════════════════════════════════════════════════════════════
# PublicationFactory
# ═══════════════════════════════════════════════════════════════════

class PublicationFactory:
    @staticmethod
    def create(db: BONDatabase, robot_name: str, group_url: str,
               status: str = "success", **kwargs) -> int:
        return db.record_publication(
            robot_name    = robot_name,
            group_url     = group_url,
            status        = status,
            post_content  = kwargs.get("post_content", "Contenu de test " + _rand_str(10)),
            campaign_name = kwargs.get("campaign_name", "test_campaign"),
            variant_id    = kwargs.get("variant_id", "v1"),
            post_type     = kwargs.get("post_type", "text_image"),
        )

    @staticmethod
    def create_history(db: BONDatabase, robot_name: str,
                        groups: list, days_back: int = 7) -> int:
        """Crée un historique de publications pour les tests anti-doublon."""
        count = 0
        for day_offset in range(days_back):
            for group in random.sample(groups, min(3, len(groups))):
                PublicationFactory.create(db, robot_name, group["url"])
                count += 1
        return count


# ═══════════════════════════════════════════════════════════════════
# DmQueueFactory
# ═══════════════════════════════════════════════════════════════════

class DmQueueFactory:
    @staticmethod
    def create(db: BONDatabase, robot_name: str,
               target_id: str = None, **kwargs) -> int:
        target_id = target_id or f"https://www.facebook.com/user/{_rand_str(8)}"
        return db.enqueue_dm(
            robot_name   = robot_name,
            target_type  = kwargs.get("target_type", "ami"),
            target_id    = target_id,
            text_content = kwargs.get("text", "Bonjour ! " + _rand_str(20)),
            media_paths  = kwargs.get("media_paths"),
            scheduled_at = kwargs.get("scheduled_at"),
        )

    @staticmethod
    def create_batch(db: BONDatabase, robot_name: str, count: int = 5) -> list:
        return [DmQueueFactory.create(db, robot_name) for _ in range(count)]


# ═══════════════════════════════════════════════════════════════════
# Seeder — jeu de données complet pour dev / tests
# ═══════════════════════════════════════════════════════════════════

class Seeder:
    """
    Popule la base avec un jeu de données complet et cohérent.
    Idempotent : vérifie si les données existent déjà avant d'insérer.
    """

    @staticmethod
    def seed_all(db: BONDatabase, robot_count: int = 3) -> dict:
        """
        Seede :
          - N robots (robot1..N) avec comptes associés
          - 5 campagnes avec 3 variantes chacune
          - 6 groupes assignés à chaque robot
          - 5 médias par robot (dont certains avec captcha)
          - 10 commentaires globaux + 5 par robot
          - 5 DM en attente par robot
        Retourne un résumé de ce qui a été créé.
        """
        summary = {"robots": [], "campaigns": [], "groups": [], "media": 0, "comments": 0}

        # Robots
        robots = RobotFactory.create_batch(db, robot_count)
        summary["robots"] = [r["robot_name"] for r in robots if r]

        # Campagnes
        campaigns = CampaignFactory.create_batch(db, 5)
        summary["campaigns"] = [c["name"] for c in campaigns if c]

        # Groupes (partagés entre tous les robots)
        groups = GroupFactory.create_batch(db, 6)
        summary["groups"] = [g["url"] for g in groups if g]

        # Assigner campagnes + groupes + médias à chaque robot
        for robot in robots:
            if not robot:
                continue
            rn = robot["robot_name"]

            # Groupes
            GroupFactory.assign_to_robot(db, rn, groups)

            # Campagnes
            CampaignFactory.assign_to_robot(db, rn, campaigns)

            # Médias (5 par robot, dont 2 avec captcha)
            medias = []
            camp_id = campaigns[0]["id"] if campaigns else None
            for i in range(5):
                m = MediaFactory.create(
                    db,
                    campaign_id  = camp_id,
                    captcha_text = f"PROMO{random.randint(10,99)}" if i < 2 else None,
                    description  = f"Description média {i+1}" if i % 2 == 0 else None,
                )
                if m:
                    medias.append(m)
                    summary["media"] += 1
            MediaFactory.assign_to_robot(db, rn, medias)

            # Commentaires spécifiques au robot
            CommentFactory.create_batch(db, 5, robot_name=rn)
            summary["comments"] += 5

            # DM en attente
            DmQueueFactory.create_batch(db, rn, 3)

        # Commentaires globaux (disponibles pour tous les robots)
        CommentFactory.create_batch(db, 10, robot_name=None)
        summary["comments"] += 10

        return summary

    @staticmethod
    def seed_minimal(db: BONDatabase) -> dict:
        """Jeu de données minimal pour tests unitaires rapides."""
        robot    = RobotFactory.create(db, "robot1", "compte_test")
        campaign = CampaignFactory.create(db, "campagne_test", variant_count=2)
        group    = GroupFactory.create(db)
        db.assign_group_to_robot("robot1", group["url"])
        db.assign_campaign_to_robot("robot1", campaign["name"])
        CommentFactory.create_batch(db, 5, "robot1")
        return {
            "robot":    robot,
            "campaign": campaign,
            "group":    group,
        }
