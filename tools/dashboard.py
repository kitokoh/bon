"""
tools/dashboard.py — Dashboard minimal pour BON

Affiche en temps réel:
- Comptes actifs et leur santé
- Publications du jour (succès/échecs)
- Dernières erreurs
- Statistiques des sélecteurs
- Groupes les plus performants

Usage:
    python -m tools.dashboard
"""

import json
import pathlib
import time
from datetime import datetime
from typing import Optional

try:
    from libs.database import get_database, BONDatabase
    from automation.selector_health import get_health_manager
    from automation.anti_block import get_anti_block_manager
except ImportError:
    from database import get_database, BONDatabase
    from selector_health import get_health_manager
    from anti_block import get_anti_block_manager


class Dashboard:
    """
    Dashboard minimal pour surveiller l'activité BON.
    
    Peut être intégré dans une interface PyQt ou utilisé en CLI.
    """
    
    def __init__(self, db: BONDatabase = None):
        self.db = db or get_database()
        self.health_manager = get_health_manager()
        self.anti_block_manager = get_anti_block_manager()
    
    def render_cli(self):
        """Affiche le dashboard en mode texte (CLI)."""
        self._clear_screen()
        
        print("=" * 70)
        print(" " * 20 + "📊 BON DASHBOARD")
        print(" " * 18 + f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Statistiques générales
        self._render_stats()
        
        # Comptes
        self._render_accounts()
        
        # Dernières erreurs
        self._render_recent_errors()
        
        # Sélecteurs critiques
        self._render_selector_health()
        
        # Anti-blocage
        self._render_anti_block_status()
        
        print("=" * 70)
        print("Appuyez sur Ctrl+C pour quitter | Refresh automatique toutes les 5s")
        print("=" * 70)
    
    def _clear_screen(self):
        """Efface l'écran."""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _render_stats(self):
        """Affiche les statistiques principales."""
        stats = self.db.get_dashboard_stats()
        
        print("\n📈 STATISTIQUES DU JOUR")
        print("-" * 70)
        
        # Ligne 1
        posts = stats.get("posts_today", 0)
        success = stats.get("successful_posts_today", 0)
        failed = stats.get("failed_posts_today", 0)
        rate = stats.get("success_rate_today", 0)
        
        status_icon = "✅" if rate >= 90 else "⚠️" if rate >= 70 else "❌"
        print(f"{status_icon} Publications: {posts} total | {success} succès | {failed} échecs ({rate}%)")
        
        # Ligne 2
        total_accounts = stats.get("total_accounts", 0)
        healthy = stats.get("healthy_accounts", 0)
        blocked = stats.get("blocked_accounts", 0)
        
        print(f"👤 Comptes: {total_accounts} total | {healthy} sains | {blocked} bloqués")
        
        # Ligne 3
        total_groups = stats.get("total_groups", 0)
        avg_score = stats.get("avg_group_score", 0)
        
        score_icon = "⭐" if avg_score >= 80 else "📊" if avg_score >= 50 else "⚠️"
        print(f"{score_icon} Groupes: {total_groups} enregistrés | Score moyen: {avg_score}/100")
        
        # Ligne 4
        errors = stats.get("errors_today", 0)
        print(f"🔴 Erreurs aujourd'hui: {errors}")
    
    def _render_accounts(self):
        """Affiche l'état des comptes."""
        accounts = self.db.get_all_accounts()
        
        print("\n👥 ÉTAT DES COMPTES")
        print("-" * 70)
        
        if not accounts:
            print("Aucun compte enregistré")
            return
        
        print(f"{'Nom':<20} {'Statut':<15} {'Santé':<8} {'Posts':<8} {'Dernière activité':<20}")
        print("-" * 70)
        
        for acc in accounts[:10]:  # Max 10 comptes
            name = acc.get("name", "N/A")[:18]
            status = acc.get("status", "healthy")
            health = acc.get("health_score", 100)
            total_posts = acc.get("total_posts", 0)
            last_activity = acc.get("last_activity_date", "Jamais")
            
            # Icône statut
            status_icon = "🟢" if status == "healthy" else "🟡" if status == "warning" else "🔴"
            status_text = f"{status_icon} {status}"
            
            # Format date
            if last_activity and last_activity != "None":
                try:
                    dt = datetime.fromisoformat(last_activity)
                    last_activity_str = dt.strftime("%m-%d %H:%M")
                except:
                    last_activity_str = "Inconnue"
            else:
                last_activity_str = "Jamais"
            
            print(f"{name:<20} {status_text:<15} {health:<8} {total_posts:<8} {last_activity_str:<20}")
        
        if len(accounts) > 10:
            print(f"... et {len(accounts) - 10} autres comptes")
    
    def _render_recent_errors(self):
        """Affiche les erreurs récentes."""
        errors = self.db.get_recent_errors(limit=5)
        
        print("\n🔴 DERNIÈRES ERREURS")
        print("-" * 70)
        
        if not errors:
            print("Aucune erreur récente")
            return
        
        for err in errors:
            ts = err.get("created_at", "Inconnue")
            error_type = err.get("error_type", "Unknown")
            step = err.get("step", "N/A")
            message = err.get("error_message", "")[:50]
            
            try:
                dt = datetime.fromisoformat(ts)
                ts_str = dt.strftime("%m-%d %H:%M")
            except:
                ts_str = ts
            
            print(f"  [{ts_str}] {error_type} - {step}: {message}")
    
    def _render_selector_health(self):
        """Affiche la santé des sélecteurs."""
        print("\n🎯 SANTÉ DES SÉLECTEURS")
        print("-" * 70)
        
        # Utiliser le fichier JSON de santé
        all_stats = self.health_manager.get_all_stats()
        
        if not all_stats:
            print("Aucune donnée de santé disponible")
            return
        
        dead_selectors = self.health_manager.detect_dead_selectors(threshold=50)
        
        if dead_selectors:
            print(f"⚠️  Sélecteurs problématiques détectés:")
            for sel in dead_selectors[:5]:
                stats = all_stats.get(sel, {})
                rate = stats.get("success_rate", 0)
                print(f"   ❌ {sel}: {rate}% de succès")
        else:
            print("✅ Tous les sélecteurs sont opérationnels")
        
        # Afficher les 5 pires sélecteurs
        sorted_selectors = sorted(
            all_stats.items(),
            key=lambda x: x[1].get("success_rate", 100)
        )[:5]
        
        if sorted_selectors:
            print("\n   Sélecteurs les moins fiables:")
            for key, stats in sorted_selectors:
                rate = stats.get("success_rate", 100)
                attempts = stats.get("total_attempts", 0)
                if attempts > 0:
                    print(f"   ⚠️  {key}: {rate}% ({attempts} tentatives)")
    
    def _render_anti_block_status(self):
        """Affiche le statut anti-blocage."""
        print("\n🛡️  STATUT ANTI-BLOCAGE")
        print("-" * 70)
        
        stats = self.anti_block_manager.get_stats()
        
        posts_today = stats.get("posts_today", 0)
        hourly_count = stats.get("hourly_count", 0)
        max_per_hour = stats.get("max_per_hour", 5)
        last_post = stats.get("last_post")
        long_pause = stats.get("long_pause_until")
        
        print(f"   Posts aujourd'hui: {posts_today}")
        print(f"   Posts cette heure: {hourly_count}/{max_per_hour}")
        
        if last_post:
            try:
                dt = datetime.fromisoformat(last_post)
                last_post_str = dt.strftime("%H:%M:%S")
            except:
                last_post_str = last_post
            print(f"   Dernier post: {last_post_str}")
        else:
            print(f"   Dernier post: Aucun")
        
        if long_pause:
            try:
                dt = datetime.fromisoformat(long_pause)
                remaining = (dt - datetime.now()).seconds // 60
                if remaining > 0:
                    print(f"   ⏸️  Pause longue en cours: {remaining} minutes restantes")
                else:
                    print(f"   ✅ Pause longue terminée")
            except:
                pass
    
    def run_loop(self, refresh_interval: int = 5):
        """
        Lance le dashboard en boucle avec rafraîchissement automatique.
        
        Args:
            refresh_interval: Intervalle de rafraîchissement en secondes
        """
        try:
            while True:
                self.render_cli()
                time.sleep(refresh_interval)
        except KeyboardInterrupt:
            print("\n\nDashboard arrêté.")
    
    def get_json_report(self) -> dict:
        """
        Génère un rapport JSON complet pour intégration PyQt.
        
        Returns:
            Dict avec toutes les données du dashboard
        """
        stats = self.db.get_dashboard_stats()
        accounts = self.db.get_all_accounts()
        recent_errors = self.db.get_recent_errors(limit=10)
        selector_health = self.health_manager.get_all_stats()
        anti_block_stats = self.anti_block_manager.get_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "general_stats": stats,
            "accounts": accounts,
            "recent_errors": recent_errors,
            "selector_health": selector_health,
            "anti_block": anti_block_stats,
            "dead_selectors": self.health_manager.detect_dead_selectors(),
            "best_groups": self.db.get_best_groups(limit=10)
        }


def main():
    """Point d'entrée CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description="BON Dashboard")
    parser.add_argument("--json", action="store_true", help="Sortie JSON au lieu de CLI")
    parser.add_argument("--no-refresh", action="store_true", help="Pas de rafraîchissement automatique")
    parser.add_argument("--interval", type=int, default=5, help="Intervalle de rafraîchissement (secondes)")
    
    args = parser.parse_args()
    
    dashboard = Dashboard()
    
    if args.json:
        # Mode JSON pour intégration
        print(json.dumps(dashboard.get_json_report(), indent=2, ensure_ascii=False))
    elif args.no_refresh:
        # Affichage unique
        dashboard.render_cli()
    else:
        # Boucle avec rafraîchissement
        print("Lancement du dashboard... (Ctrl+C pour arrêter)")
        dashboard.run_loop(refresh_interval=args.interval)


if __name__ == "__main__":
    main()
