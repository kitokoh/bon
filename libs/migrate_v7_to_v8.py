"""
migrate_v7_to_v8.py — Migration automatique JSON → SQL

Lance ce script UNE SEULE FOIS pour migrer:
  - campaigns.json  → tables campaigns + campaign_variants
  - groups.json     → table groups
  - {session}.json  → table sessions
  - telegram.json   → table config_kv

Usage:
    python -m libs.migrate_v7_to_v8 [--data-dir /path/to/bon_v7/data]
"""
import json, pathlib, sys, argparse

try:
    from libs.database import get_database
    from libs.config_manager import SESSIONS_DIR, APP_DIR
    from libs.log_emitter import emit
except ImportError:
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
    from libs.database import get_database
    from libs.config_manager import SESSIONS_DIR, APP_DIR
    from libs.log_emitter import emit


def migrate_campaigns(data_dir: pathlib.Path, db) -> int:
    """Migre campaigns.json → tables campaigns + campaign_variants + media_assets."""
    path = data_dir / "campaigns" / "campaigns.json"
    if not path.exists():
        print(f"[MIGRATE] campaigns.json non trouvé : {path}")
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    campaigns = data.get("campaigns", {})
    count = 0
    for camp_key, camp in campaigns.items():
        camp_id = db.upsert_campaign(
            name=camp.get("name", camp_key),
            description=camp.get("description", ""),
            language=data.get("global_settings", {}).get("default_language", "fr"),
            active=camp.get("active", True)
        )
        for var in camp.get("variants", []):
            db.upsert_variant(
                campaign_id=camp_id,
                variant_key=var.get("id", "v1"),
                text_fr=var.get("text_fr"),
                text_en=var.get("text_en"),
                text_ar=var.get("text_ar"),
                cta=var.get("cta"),
                weight=var.get("weight", 1),
                image_paths=var.get("images", []),
            )
        count += 1
    print(f"[MIGRATE] {count} campagnes migrées depuis {path}")
    return count


def migrate_groups(data_dir: pathlib.Path, db) -> int:
    """Migre groups.json → table groups."""
    path = data_dir / "groups" / "groups.json"
    if not path.exists():
        print(f"[MIGRATE] groups.json non trouvé : {path}")
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    groups = data.get("groups", [])
    count = db.import_groups_from_list(groups)
    print(f"[MIGRATE] {count} groupes migrés depuis {path}")
    return count


def migrate_sessions(db) -> int:
    """Migre {session}.json → table sessions."""
    count = 0
    for path in SESSIONS_DIR.glob("*.json"):
        if path.name.endswith("_state.json"):
            continue
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
            session_name = config.get("session_name") or path.stem
            if not session_name:
                continue
            db.upsert_session(session_name, config)
            count += 1
            print(f"[MIGRATE] Session '{session_name}' migrée")
        except Exception as e:
            print(f"[MIGRATE] Erreur session {path}: {e}")
    return count


def migrate_telegram(db) -> bool:
    """Migre logs/telegram.json → config_kv."""
    logs_dir = APP_DIR / "logs"
    path = logs_dir / "telegram.json"
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        token   = data.get("token","").strip()
        chat_id = data.get("chat_id","").strip()
        if token and chat_id:
            db.set_telegram_config(token, chat_id)
            print(f"[MIGRATE] Config Telegram migrée depuis {path}")
            return True
    except Exception as e:
        print(f"[MIGRATE] Erreur Telegram: {e}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Migration BON v7 → v8 (JSON → SQL)")
    parser.add_argument("--data-dir", default=None, help="Répertoire data (défaut: détection auto)")
    args = parser.parse_args()

    # Détecter le répertoire data
    if args.data_dir:
        data_dir = pathlib.Path(args.data_dir)
    else:
        # Chercher depuis le répertoire courant
        candidates = [
            pathlib.Path("data"),
            pathlib.Path(__file__).parent.parent / "data",
        ]
        data_dir = next((c for c in candidates if c.exists()), pathlib.Path("data"))

    print(f"[MIGRATE] Démarrage migration v7→v8")
    print(f"[MIGRATE] data_dir : {data_dir.resolve()}")

    db = get_database()
    total = 0
    total += migrate_campaigns(data_dir, db)
    total += migrate_groups(data_dir, db)
    total += migrate_sessions(db)
    migrate_telegram(db)

    print(f"\n[MIGRATE] Migration terminée — {total} éléments migrés")
    print("[MIGRATE] Vous pouvez maintenant archiver les fichiers JSON (ne pas supprimer avant validation)")


if __name__ == "__main__":
    main()
