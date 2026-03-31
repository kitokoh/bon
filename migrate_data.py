"""
migrate_data.py — Outil de migration depuis l'ancien format (data.json)
vers le nouveau format de session par compte.

Utilisez cet outil une fois pour migrer votre configuration existante.
  python migrate_data.py --data data.json --session mon_compte
"""
import argparse
import json
import pathlib
import sys

try:
    from libs.config_manager import (
        get_session_config_path, SESSIONS_DIR, MEDIA_DIR, save_json
    )
    from libs.log_emitter import emit
except ImportError:
    # Exécution depuis la racine du projet
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from libs.config_manager import (
        get_session_config_path, SESSIONS_DIR, MEDIA_DIR, save_json
    )
    from libs.log_emitter import emit


def load_json(path: pathlib.Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"✗ Impossible de lire {path} : {e}")
        sys.exit(1)


def normalize_image_path(image_path: str, session_name: str) -> str:
    """
    Normalise un chemin d'image absolu Windows vers un chemin relatif portable.
    Les images doivent être copiées manuellement dans :
      {MEDIA_DIR}/{session_name}/
    """
    if not image_path:
        return ""
    p = pathlib.Path(image_path)
    # Retourner juste le nom du fichier — sera résolu par resolve_media_path()
    return p.name


def migrate(data_path: pathlib.Path, session_name: str, dry_run: bool = False) -> dict:
    """
    Migre data.json vers le format de session v2.

    Returns:
        Le dictionnaire de config migré
    """
    data = load_json(data_path)
    print(f"\n→ Migration de '{data_path}' vers session '{session_name}'")

    # ── Posts ────────────────────────────────────────────────
    old_posts = data.get("posts", [])
    new_posts = []
    for p in old_posts:
        new_posts.append({
            "text": p.get("text", ""),
            "image": normalize_image_path(p.get("image", ""), session_name),
            "weight": 1,
        })

    # Support de l'ancien format data1.json (stories)
    old_stories = data.get("stories", [])
    for s in old_stories:
        new_posts.append({
            "text": s.get("text", ""),
            "image": normalize_image_path(s.get("image", ""), session_name),
            "weight": 1,
        })

    # ── Groupes ──────────────────────────────────────────────
    groups = data.get("groups", [])
    # Nettoyer les URLs (supprimer paramètres de tracking)
    clean_groups = []
    for url in groups:
        clean = url.split("?")[0].rstrip("/") + "/"
        clean_groups.append(clean)

    # ── Config finale ────────────────────────────────────────
    config = {
        "session_name": session_name,
        "storage_state": str(SESSIONS_DIR / f"{session_name}_state.json"),
        "max_groups_per_run": 10,
        "delay_between_groups": [60, 120],
        "max_runs_per_day": 2,
        "last_run_ts": None,
        "posts": new_posts,
        "groups": clean_groups,
    }

    # ── Résumé ───────────────────────────────────────────────
    print(f"  Posts migrés   : {len(new_posts)}")
    print(f"  Groupes migrés : {len(clean_groups)}")
    if new_posts and new_posts[0]["image"]:
        media_target = MEDIA_DIR / session_name
        print(f"\n  ⚠ Copiez vos images dans :")
        print(f"    {media_target}")
        images = [p["image"] for p in new_posts if p["image"]]
        for img in images[:5]:
            print(f"      • {img}")
        if len(images) > 5:
            print(f"      ... et {len(images) - 5} autre(s)")

    if dry_run:
        print("\n[DRY RUN] Aucune écriture effectuée.")
        print("Config qui serait créée :")
        print(json.dumps(config, indent=2, ensure_ascii=False))
    else:
        dest = get_session_config_path(session_name)
        save_json(dest, config)
        print(f"\n✓ Config sauvegardée : {dest}")
        print(f"\nProchaine étape : créer la session (login) :")
        print(f"  python -m bon login --session {session_name}")

    return config


def main():
    parser = argparse.ArgumentParser(
        description="Migration data.json → format session BON v2"
    )
    parser.add_argument("--data", required=True,
                        help="Chemin vers l'ancien data.json (ou data1.json)")
    parser.add_argument("--session", required=True,
                        help="Nom de la session à créer (ex: compte1)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simuler sans écrire (preview)")
    args = parser.parse_args()

    data_path = pathlib.Path(args.data)
    if not data_path.exists():
        print(f"✗ Fichier introuvable : {data_path}")
        sys.exit(1)

    migrate(data_path, args.session, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
