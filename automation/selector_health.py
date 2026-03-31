"""
automation/selector_health.py — Gestion de la santé des sélecteurs

Surveille les taux de succès des sélecteurs et détecte automatiquement
les sélecteurs morts ou dégradés.
"""

import json
import pathlib
from datetime import datetime
from typing import Optional, Dict, List


class SelectorHealthManager:
    """
    Gère la santé des sélecteurs Facebook.
    
    - Enregistre les tentatives (succès/échec)
    - Calcule les taux de réussite
    - Détecte les sélecteurs morts (< 50% de succès)
    - Propose des alternatives
    """
    
    def __init__(self, health_file: str = "logs/selector_health.json"):
        self.health_file = pathlib.Path(health_file)
        self.health_file.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()
    
    def _load(self) -> dict:
        """Charge le fichier de santé."""
        if self.health_file.exists():
            try:
                with open(self.health_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save(self):
        """Sauvegarde le fichier de santé."""
        with open(self.health_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def record_success(self, selector_key: str, used_selector: str):
        """Enregistre un succès pour un sélecteur."""
        now = datetime.now().isoformat()
        
        if selector_key not in self.data:
            self.data[selector_key] = {
                "working_selector": used_selector,
                "success_rate": 100,
                "last_success": now,
                "total_attempts": 1,
                "successful_attempts": 1,
                "failed_attempts": 0,
                "last_failure_reason": None,
                "alternative_selectors": []
            }
        else:
            entry = self.data[selector_key]
            entry["total_attempts"] += 1
            entry["successful_attempts"] += 1
            entry["last_success"] = now
            entry["working_selector"] = used_selector
            
            # Recalculer le taux de succès
            if entry["total_attempts"] > 0:
                entry["success_rate"] = round(
                    (entry["successful_attempts"] / entry["total_attempts"]) * 100
                )
        
        self._save()
    
    def record_failure(self, selector_key: str, reason: str, tried_selectors: List[str]):
        """Enregistre un échec pour un sélecteur."""
        now = datetime.now().isoformat()
        
        if selector_key not in self.data:
            self.data[selector_key] = {
                "working_selector": None,
                "success_rate": 0,
                "last_success": None,
                "total_attempts": 1,
                "successful_attempts": 0,
                "failed_attempts": 1,
                "last_failure_reason": reason,
                "alternative_selectors": tried_selectors
            }
        else:
            entry = self.data[selector_key]
            entry["total_attempts"] += 1
            entry["failed_attempts"] += 1
            entry["last_failure_reason"] = reason
            
            # Ajouter les sélecteurs testés comme alternatives potentielles
            for sel in tried_selectors:
                if sel not in entry.get("alternative_selectors", []):
                    if "alternative_selectors" not in entry:
                        entry["alternative_selectors"] = []
                    entry["alternative_selectors"].append(sel)
            
            # Recalculer le taux de succès
            if entry["total_attempts"] > 0:
                entry["success_rate"] = round(
                    (entry["successful_attempts"] / entry["total_attempts"]) * 100
                )
        
        self._save()
    
    def is_healthy(self, selector_key: str, min_rate: int = 50) -> bool:
        """Vérifie si un sélecteur est en bonne santé."""
        if selector_key not in self.data:
            return True  # Pas de données = on considère sain
        
        return self.data[selector_key].get("success_rate", 0) >= min_rate
    
    def get_working_selector(self, selector_key: str) -> Optional[str]:
        """Retourne le dernier sélecteur fonctionnel connu."""
        if selector_key not in self.data:
            return None
        return self.data[selector_key].get("working_selector")
    
    def get_alternatives(self, selector_key: str) -> List[str]:
        """Retourne la liste des sélecteurs alternatifs."""
        if selector_key not in self.data:
            return []
        return self.data[selector_key].get("alternative_selectors", [])
    
    def get_stats(self, selector_key: str) -> Optional[dict]:
        """Retourne les statistiques complètes d'un sélecteur."""
        return self.data.get(selector_key)
    
    def get_all_stats(self) -> dict:
        """Retourne les statistiques de tous les sélecteurs."""
        return self.data
    
    def detect_dead_selectors(self, threshold: int = 30) -> List[str]:
        """Détecte les sélecteurs morts (taux de succès < threshold)."""
        dead = []
        for key, entry in self.data.items():
            if entry.get("success_rate", 100) < threshold:
                dead.append(key)
        return dead
    
    def generate_report(self) -> str:
        """Génère un rapport textuel de la santé des sélecteurs."""
        lines = ["=" * 60, "RAPPORT DE SANTÉ DES SÉLECTEURS", "=" * 60, ""]
        
        for key, entry in sorted(self.data.items()):
            rate = entry.get("success_rate", 0)
            status = "✓" if rate >= 80 else "⚠" if rate >= 50 else "✗"
            
            lines.append(f"{status} {key}")
            lines.append(f"   Taux de succès: {rate}%")
            lines.append(f"   Tentatives: {entry.get('total_attempts', 0)}")
            lines.append(f"   Succès: {entry.get('successful_attempts', 0)}")
            lines.append(f"   Échecs: {entry.get('failed_attempts', 0)}")
            
            if entry.get("last_failure_reason"):
                lines.append(f"   Dernier échec: {entry['last_failure_reason']}")
            
            if entry.get("alternative_selectors"):
                lines.append(f"   Alternatives: {len(entry['alternative_selectors'])}")
            
            lines.append("")
        
        # Résumé
        dead = self.detect_dead_selectors()
        if dead:
            lines.append("⚠️  SÉLECTEURS MORTS DÉTECTÉS:")
            for d in dead:
                lines.append(f"   - {d}")
        else:
            lines.append("✓ Tous les sélecteurs sont opérationnels.")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# Instance globale pour usage facile
_health_manager = None


def get_health_manager() -> SelectorHealthManager:
    """Retourne l'instance globale du gestionnaire de santé."""
    global _health_manager
    if _health_manager is None:
        _health_manager = SelectorHealthManager()
    return _health_manager


if __name__ == "__main__":
    # Test/demo
    hm = SelectorHealthManager()
    
    # Simuler quelques enregistrements
    hm.record_success("submit", "aria=Publier")
    hm.record_success("submit", "aria=Publier")
    hm.record_failure("submit", "Element not found", ["aria=Publier", "[role='button']"])
    hm.record_success("input", "div[role='textbox']")
    
    print(hm.generate_report())
