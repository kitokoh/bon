"""
variant_selector.py v11 — Sélection intelligente des variants

Problème v9 : pick_random_variant() sélectionne au hasard pondéré sans tenir
compte de l'historique → même variant répété dans le même groupe.

Solution v10 : VariantSelector avec exclusion des variants récents.
  1. Charge les publications récentes (configurable, défaut 30j)
  2. Pour chaque (robot, groupe), exclut les variants déjà utilisés
  3. Si tous les variants ont été utilisés → réinitialise (rotation complète)
  4. Sélection pondérée parmi les variants disponibles

Usage :
    from libs.variant_selector import pick_variant
    variant = pick_variant(db, robot_name="robot1",
                           campaign_name="farmoos",
                           group_url="https://fb.com/groups/...",
                           language="fr")
"""
import random
from typing import Optional, List, Dict
from datetime import datetime, timedelta


def pick_variant(db, robot_name: str, campaign_name: str,
                 group_url: str = None, language: str = "fr",
                 exclusion_days: int = 30,
                 exclude_cross_robot: bool = False) -> Optional[Dict]:
    """
    Sélectionne un variant en évitant les répétitions récentes.

    Args:
        db             : instance BONDatabase
        robot_name     : nom du robot
        campaign_name  : nom de la campagne
        group_url      : URL du groupe (pour l'anti-répétition)
        language       : langue du texte à retourner
        exclusion_days : fenêtre d'exclusion en jours (défaut 30)
        exclude_cross_robot : si True, exclut les variants déjà postés par *tout* robot
                               sur ce groupe (rotation multi-robots).

    Returns:
        Dict variant avec champ "text" dans la langue demandée, ou None.
    """
    camp = db.get_campaign_by_name(campaign_name)
    if not camp:
        return None

    all_variants = db.get_variants(camp["id"])
    if not all_variants:
        return None

    # Récupérer les variants déjà utilisés dans ce groupe récemment
    used_keys = set()
    if group_url:
        grp = db.get_group_by_url(group_url)
        if grp:
            since = (datetime.now() - timedelta(days=exclusion_days)).isoformat()
            if exclude_cross_robot:
                rows = db._query(
                    """SELECT variant_id FROM publications
                       WHERE group_id=? AND status='success'
                       AND campaign_name=? AND created_at>=?""",
                    (grp["id"], campaign_name, since)
                )
            else:
                rows = db._query(
                    """SELECT variant_id FROM publications
                       WHERE robot_name=? AND group_id=? AND status='success'
                       AND campaign_name=? AND created_at>=?""",
                    (robot_name, grp["id"], campaign_name, since)
                )
            used_keys = {r["variant_id"] for r in rows if r.get("variant_id")}

    # Variants disponibles (non utilisés récemment)
    available = [v for v in all_variants
                 if v.get("variant_key") not in used_keys]

    # Si tous utilisés → réinitialiser (rotation complète)
    if not available:
        available = all_variants
        emit_reset = True
    else:
        emit_reset = False

    # Sélection pondérée
    weights = [max(1, v.get("weight", 1)) for v in available]
    chosen  = dict(random.choices(available, weights=weights, k=1)[0])

    # Ajouter le texte dans la langue demandée
    lang_field = f"text_{language}" if language in ("fr", "en", "ar") else "text_fr"
    chosen["text"] = chosen.get(lang_field) or chosen.get("text_fr") or ""

    if emit_reset:
        try:
            from libs.log_emitter import emit
            emit("DEBUG", "VARIANT_ROTATION_RESET",
                 robot=robot_name, campaign=campaign_name,
                 group=group_url[:60] if group_url else "?")
        except Exception:
            pass

    return chosen


def get_variant_history(db, robot_name: str, campaign_name: str,
                         group_url: str = None, days: int = 30) -> List[str]:
    """Retourne la liste des variant_keys utilisés récemment."""
    camp = db.get_campaign_by_name(campaign_name)
    if not camp:
        return []
    since = (datetime.now() - timedelta(days=days)).isoformat()
    where = "robot_name=? AND campaign_name=? AND status='success' AND created_at>=?"
    params = [robot_name, campaign_name, since]
    if group_url:
        grp = db.get_group_by_url(group_url)
        if grp:
            where += " AND group_id=?"
            params.append(grp["id"])
    rows = db._query(
        f"SELECT variant_id FROM publications WHERE {where}", tuple(params)
    )
    return [r["variant_id"] for r in rows if r.get("variant_id")]
