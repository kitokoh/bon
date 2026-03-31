"""
automation/anti_block.py — Gestion des limitations anti-blocage

Implémente les règles pour éviter le blocage Facebook:
- Maximum 5 groupes par heure
- Pause aléatoire 30–120 secondes entre les posts
- Pause longue après 3 publications
- Pas de même texte deux fois de suite
- Pas de même image plus de 2 fois
"""

import random
import time
import json
import pathlib
from datetime import datetime, timedelta
from typing import List, Optional, Set


class AntiBlockManager:
    """
    Gère les limitations anti-blocage Facebook.
    
    Règles implémentées:
    - max_groups_per_hour: Maximum 5 groupes par heure
    - delay_between_posts: Pause aléatoire 30-120 secondes
    - long_pause_after: Pause longue après N publications
    - no_duplicate_text: Pas de même texte deux fois de suite
    - no_overused_image: Pas de même image plus de 2 fois
    """
    
    def __init__(self, config_file: str = "data/anti_block_state.json"):
        self.config_file = pathlib.Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()
        
        # Configuration par défaut
        self.max_groups_per_hour = 5
        self.delay_min_seconds = 30
        self.delay_max_seconds = 120
        self.long_pause_after_posts = 3
        self.long_pause_min_minutes = 30
        self.long_pause_max_minutes = 60
        self.max_image_uses = 2
    
    def _load(self) -> dict:
        """Charge l'état depuis le fichier."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {
            "posts_today": [],
            "texts_used": [],
            "images_used": {},
            "last_post_time": None,
            "long_pause_until": None,
            "hourly_counts": {}
        }
    
    def _save(self):
        """Sauvegarde l'état."""
        self._cleanup_old_data()
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
    
    def _cleanup_old_data(self):
        """Nettoie les données anciennes (> 24h)."""
        now = datetime.now()
        cutoff = now - timedelta(hours=24)
        
        # Nettoyer les posts d'aujourd'hui
        if "posts_today" in self.state:
            self.state["posts_today"] = [
                p for p in self.state["posts_today"]
                if datetime.fromisoformat(p["time"]) > cutoff
            ]
        
        # Nettoyer les textes utilisés (garder seulement les 10 derniers)
        if "texts_used" in self.state:
            self.state["texts_used"] = self.state["texts_used"][-10:]
        
        # Nettoyer les counts horaires (> 2 heures)
        if "hourly_counts" in self.state:
            current_hour = now.strftime("%Y-%m-%d-%H")
            self.state["hourly_counts"] = {
                k: v for k, v in self.state["hourly_counts"].items()
                if k >= current_hour
            }
    
    def can_post(self) -> tuple[bool, str]:
        """
        Vérifie si on peut poster maintenant.
        
        Returns:
            (can_post, reason)
        """
        now = datetime.now()
        
        # Vérifier pause longue
        if self.state.get("long_pause_until"):
            pause_until = datetime.fromisoformat(self.state["long_pause_until"])
            if now < pause_until:
                remaining = (pause_until - now).seconds // 60
                return False, f"Pause longue en cours, attendez {remaining} minutes"
            else:
                self.state["long_pause_until"] = None
        
        # Vérifier limite horaire
        current_hour = now.strftime("%Y-%m-%d-%H")
        hourly_count = self.state.get("hourly_counts", {}).get(current_hour, 0)
        if hourly_count >= self.max_groups_per_hour:
            return False, f"Limite horaire atteinte ({hourly_count}/{self.max_groups_per_hour})"
        
        # Vérifier délai entre posts
        if self.state.get("last_post_time"):
            last_post = datetime.fromisoformat(self.state["last_post_time"])
            elapsed = (now - last_post).seconds
            min_delay = random.randint(self.delay_min_seconds, self.delay_max_seconds)
            if elapsed < min_delay:
                remaining = min_delay - elapsed
                return False, f"Attendez {remaining} secondes avant le prochain post"
        
        return True, "OK"
    
    def record_post(self, group_url: str, text: str, images: List[str]):
        """Enregistre un post effectué."""
        now = datetime.now()
        
        # Ajouter aux posts d'aujourd'hui
        post_record = {
            "time": now.isoformat(),
            "group": group_url,
            "text_hash": hash(text) % 1000000,
            "images": images
        }
        self.state.setdefault("posts_today", []).append(post_record)
        
        # Mettre à jour le dernier temps de post
        self.state["last_post_time"] = now.isoformat()
        
        # Mettre à jour le compteur horaire
        current_hour = now.strftime("%Y-%m-%d-%H")
        hourly_counts = self.state.setdefault("hourly_counts", {})
        hourly_counts[current_hour] = hourly_counts.get(current_hour, 0) + 1
        
        # Mettre à jour l'historique des textes
        self.state.setdefault("texts_used", []).append(text)
        if len(self.state["texts_used"]) > 10:
            self.state["texts_used"] = self.state["texts_used"][-10:]
        
        # Mettre à jour le comptage des images
        images_used = self.state.setdefault("images_used", {})
        for img in images:
            images_used[img] = images_used.get(img, 0) + 1
        
        # Vérifier si pause longue nécessaire
        posts_count = len(self.state["posts_today"])
        if posts_count > 0 and posts_count % self.long_pause_after_posts == 0:
            pause_minutes = random.randint(
                self.long_pause_min_minutes,
                self.long_pause_max_minutes
            )
            self.state["long_pause_until"] = (
                now + timedelta(minutes=pause_minutes)
            ).isoformat()
            print(f"[ANTI-BLOCK] Pause longue activée: {pause_minutes} minutes")
        
        self._save()
    
    def get_next_text(self, available_texts: List[str]) -> Optional[str]:
        """
        Sélectionne un texte qui n'a pas été utilisé récemment.
        
        Args:
            available_texts: Liste des textes disponibles
        
        Returns:
            Le texte sélectionné ou None si tous ont été utilisés
        """
        used_hashes = {hash(t) % 1000000 for t in self.state.get("texts_used", [])[-5:]}
        
        candidates = [
            t for t in available_texts
            if (hash(t) % 1000000) not in used_hashes
        ]
        
        if not candidates:
            # Fallback: prendre un texte au hasard si tous ont été utilisés
            return random.choice(available_texts) if available_texts else None
        
        return random.choice(candidates)
    
    def get_valid_images(
        self,
        available_images: List[str],
        max_images: int = 5
    ) -> List[str]:
        """
        Sélectionne des images qui n'ont pas été trop utilisées.
        
        Args:
            available_images: Liste des images disponibles
            max_images: Nombre maximum d'images à retourner
        
        Returns:
            Liste d'images valides
        """
        images_used = self.state.get("images_used", {})
        
        # Filtrer les images trop utilisées
        valid = [
            img for img in available_images
            if images_used.get(img, 0) < self.max_image_uses
        ]
        
        if not valid:
            # Fallback: réinitialiser les compteurs si toutes les images sont épuisées
            self.state["images_used"] = {}
            valid = available_images
        
        # Sélectionner aléatoirement
        selected = random.sample(valid, min(len(valid), max_images))
        return selected
    
    def wait_if_needed(self) -> bool:
        """
        Attend si nécessaire selon les règles anti-blocage.
        
        Returns:
            True si une attente a eu lieu, False sinon
        """
        can_post, reason = self.can_post()
        
        if can_post:
            return False
        
        if "Pause longue" in reason:
            # Pause longue: on ne fait rien, l'utilisateur doit attendre
            print(f"[ANTI-BLOCK] {reason}")
            return False
        
        if "Attendez" in reason:
            # Délai normal: on attend automatiquement
            seconds = int(reason.split()[1])
            print(f"[ANTI-BLOCK] {reason}")
            time.sleep(seconds)
            return True
        
        return False
    
    def apply_random_delay(self, min_s: int = None, max_s: int = None):
        """Applique un délai aléatoire humain."""
        min_s = min_s or self.delay_min_seconds
        max_s = max_s or self.delay_max_seconds
        delay = random.uniform(min_s, max_s)
        print(f"[ANTI-BLOCK] Pause de {delay:.1f} secondes...")
        time.sleep(delay)
    
    def get_stats(self) -> dict:
        """Retourne les statistiques actuelles."""
        now = datetime.now()
        current_hour = now.strftime("%Y-%m-%d-%H")
        
        return {
            "posts_today": len(self.state.get("posts_today", [])),
            "hourly_count": self.state.get("hourly_counts", {}).get(current_hour, 0),
            "max_per_hour": self.max_groups_per_hour,
            "last_post": self.state.get("last_post_time"),
            "long_pause_until": self.state.get("long_pause_until"),
            "unique_texts_used": len(set(self.state.get("texts_used", []))),
            "unique_images_used": len(self.state.get("images_used", {}))
        }
    
    def reset_daily(self):
        """Réinitialise les compteurs quotidiens."""
        self.state["posts_today"] = []
        self.state["texts_used"] = []
        self.state["images_used"] = {}
        self.state["long_pause_until"] = None
        self._save()


# Instance globale
_anti_block_manager = None


def get_anti_block_manager() -> AntiBlockManager:
    """Retourne l'instance globale."""
    global _anti_block_manager
    if _anti_block_manager is None:
        _anti_block_manager = AntiBlockManager()
    return _anti_block_manager


if __name__ == "__main__":
    # Demo
    abm = AntiBlockManager()
    
    print("Statistiques initiales:")
    print(json.dumps(abm.get_stats(), indent=2))
    
    print("\nSimulation de posts...")
    for i in range(3):
        can, reason = abm.can_post()
        print(f"Post {i+1}: {reason}")
        if can:
            abm.record_post(
                f"https://facebook.com/groups/test{i}/",
                f"Texte de test {i}",
                [f"image{i}.jpg"]
            )
    
    print("\nStatistiques après simulation:")
    print(json.dumps(abm.get_stats(), indent=2))
