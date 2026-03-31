"""
database.py — Base de données SQLite pour suivi professionnel

Tables:
- accounts: Gestion des comptes Facebook avec score de santé
- groups: Groupes avec scoring et historique
- publications: Historique des publications
- errors: Journal des erreurs
- selector_stats: Statistiques des sélecteurs
"""

import sqlite3
import json
import pathlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

try:
    from libs.log_emitter import emit
except ImportError:
    from log_emitter import emit


class BONDatabase:
    """
    Base de données SQLite pour le suivi professionnel des activités.
    
    Remplace les fichiers JSON par une vraie base de données relationnelle.
    """
    
    def __init__(self, db_path: str = "logs/bon.db"):
        self.db_path = pathlib.Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager pour les connexions DB."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialise la base de données avec toutes les tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Table: accounts - Gestion des comptes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    email TEXT,
                    profile_url TEXT,
                    
                    -- Santé du compte
                    health_score INTEGER DEFAULT 100,
                    status TEXT DEFAULT 'healthy',
                    status_reason TEXT,
                    
                    -- Statistiques
                    total_posts INTEGER DEFAULT 0,
                    successful_posts INTEGER DEFAULT 0,
                    failed_posts INTEGER DEFAULT 0,
                    blocked_count INTEGER DEFAULT 0,
                    
                    -- Timing
                    last_post_date TEXT,
                    last_activity_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Configuration
                    max_groups_per_day INTEGER DEFAULT 20,
                    cooldown_until TEXT,
                    warmup_completed BOOLEAN DEFAULT FALSE,
                    
                    -- Session storage (JSON)
                    storage_state TEXT
                )
            """)
            
            # Table: groups - Groupes Facebook avec scoring
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    name TEXT,
                    category TEXT,
                    language TEXT DEFAULT 'fr',
                    
                    -- Scoring
                    quality_score INTEGER DEFAULT 50,
                    members_count INTEGER,
                    activity_level TEXT,
                    
                    -- Statistiques
                    total_posts INTEGER DEFAULT 0,
                    successful_posts INTEGER DEFAULT 0,
                    failed_posts INTEGER DEFAULT 0,
                    rejected_posts INTEGER DEFAULT 0,
                    
                    -- Timing
                    last_post_date TEXT,
                    first_seen_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Metadata
                    metadata TEXT
                )
            """)
            
            # Table: publications - Historique des publications
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS publications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    group_id INTEGER NOT NULL,
                    campaign_name TEXT,
                    variant_id TEXT,
                    text_content TEXT,
                    images TEXT,
                    
                    -- Résultat
                    status TEXT NOT NULL,
                    error_message TEXT,
                    screenshot_path TEXT,
                    
                    -- Timing
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    published_at TEXT,
                    
                    FOREIGN KEY (account_id) REFERENCES accounts(id),
                    FOREIGN KEY (group_id) REFERENCES groups(id)
                )
            """)
            
            # Table: errors - Journal des erreurs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER,
                    group_id INTEGER,
                    error_type TEXT NOT NULL,
                    error_message TEXT,
                    step TEXT,
                    selector_key TEXT,
                    screenshot_path TEXT,
                    html_snapshot_path TEXT,
                    
                    -- Timing
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (account_id) REFERENCES accounts(id),
                    FOREIGN KEY (group_id) REFERENCES groups(id)
                )
            """)
            
            # Table: selector_stats - Statistiques des sélecteurs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS selector_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    selector_key TEXT UNIQUE NOT NULL,
                    working_selector TEXT,
                    
                    -- Statistiques
                    total_attempts INTEGER DEFAULT 0,
                    successful_attempts INTEGER DEFAULT 0,
                    failed_attempts INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 100.0,
                    
                    -- Timing
                    last_success_date TEXT,
                    last_failure_date TEXT,
                    last_failure_reason TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table: account_blocks - Historique des blocages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    block_type TEXT NOT NULL,
                    reason TEXT,
                    duration_hours INTEGER,
                    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    ended_at TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    
                    FOREIGN KEY (account_id) REFERENCES accounts(id)
                )
            """)
            
            # Index pour performances
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_publications_account ON publications(account_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_publications_group ON publications(group_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_publications_status ON publications(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_account ON errors(account_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_created ON errors(created_at)")
            
            emit("INFO", "DATABASE_INITIALIZED", path=str(self.db_path))
    
    # ==================== ACCOUNTS ====================
    
    def create_account(self, name: str, email: str = None, profile_url: str = None) -> int:
        """Crée un nouveau compte."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO accounts (name, email, profile_url, last_activity_date)
                VALUES (?, ?, ?, ?)
            """, (name, email, profile_url, datetime.now().isoformat()))
            return cursor.lastrowid
    
    def get_account(self, name: str) -> Optional[Dict]:
        """Récupère un compte par son nom."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts WHERE name = ?", (name,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_account_by_id(self, account_id: int) -> Optional[Dict]:
        """Récupère un compte par son ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_account_health(self, account_id: int, health_score: int, 
                             status: str = None, status_reason: str = None):
        """Met à jour la santé d'un compte."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE accounts 
                SET health_score = ?, status = COALESCE(?, status), 
                    status_reason = COALESCE(?, status_reason),
                    updated_at = ?
                WHERE id = ?
            """, (health_score, status, status_reason, datetime.now().isoformat(), account_id))
    
    def set_account_status(self, account_id: int, status: str, reason: str = None):
        """
        Définit le statut d'un compte.
        
        Statuts possibles:
        - healthy: Compte sain, peut publier
        - warning: Avertissement, réduire le rythme
        - temporarily_blocked: Bloqué temporairement (24-72h)
        - session_expired: Session expirée, besoin de relogin
        """
        now = datetime.now()
        cooldown_until = None
        
        if status == "temporarily_blocked":
            # Cooldown de 24 à 72 heures selon la gravité
            cooldown_hours = 24
            cooldown_until = (now + timedelta(hours=cooldown_hours)).isoformat()
        elif status == "warning":
            # Cooldown de 2-4 heures
            cooldown_hours = 3
            cooldown_until = (now + timedelta(hours=cooldown_hours)).isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE accounts 
                SET status = ?, status_reason = ?, cooldown_until = ?, updated_at = ?
                WHERE id = ?
            """, (status, reason, cooldown_until, now.isoformat(), account_id))
    
    def can_account_post(self, account_id: int) -> tuple[bool, str]:
        """Vérifie si un compte peut poster."""
        account = self.get_account_by_id(account_id)
        if not account:
            return False, "Compte inexistant"
        
        # Vérifier cooldown
        if account.get("cooldown_until"):
            cooldown = datetime.fromisoformat(account["cooldown_until"])
            if datetime.now() < cooldown:
                remaining = (cooldown - datetime.now()).seconds // 3600
                return False, f"Compte en cooldown, attendez {remaining}h"
        
        # Vérifier statut
        status = account.get("status", "healthy")
        if status == "temporarily_blocked":
            return False, "Compte temporairement bloqué"
        elif status == "session_expired":
            return False, "Session expirée, reconnectez-vous"
        
        # Vérifier limite quotidienne
        today = datetime.now().date().isoformat()
        posts_today = self.get_account_posts_today(account_id)
        max_per_day = account.get("max_groups_per_day", 20)
        
        if posts_today >= max_per_day:
            return False, f"Limite quotidienne atteinte ({posts_today}/{max_per_day})"
        
        return True, "OK"
    
    def get_account_posts_today(self, account_id: int) -> int:
        """Compte le nombre de posts aujourd'hui."""
        today = datetime.now().date().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM publications 
                WHERE account_id = ? AND DATE(created_at) = ?
            """, (account_id, today))
            return cursor.fetchone()[0]
    
    def record_account_activity(self, account_id: int, success: bool):
        """Enregistre une activité de compte."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Mettre à jour les compteurs
            if success:
                cursor.execute("""
                    UPDATE accounts 
                    SET successful_posts = successful_posts + 1,
                        total_posts = total_posts + 1,
                        last_post_date = ?,
                        last_activity_date = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), datetime.now().isoformat(), 
                      datetime.now().isoformat(), account_id))
            else:
                cursor.execute("""
                    UPDATE accounts 
                    SET failed_posts = failed_posts + 1,
                        total_posts = total_posts + 1,
                        last_activity_date = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), datetime.now().isoformat(), account_id))
    
    def get_all_accounts(self) -> List[Dict]:
        """Récupère tous les comptes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def ensure_account_exists(self, name: str, email: str = None, profile_url: str = None) -> int:
        """Crée un compte s'il n'existe pas déjà, retourne l'ID."""
        existing = self.get_account(name)
        if existing:
            return existing['id']
        return self.create_account(name, email, profile_url)
    
    def get_account_status(self, name: str) -> Optional[str]:
        """Récupère le statut d'un compte par son nom."""
        account = self.get_account(name)
        return account['status'] if account else None
    
    def update_account_status(self, name: str, status: str, reason: str = None):
        """Met à jour le statut d'un compte par son nom."""
        account_id = self.ensure_account_exists(name)
        self.set_account_status(account_id, status, reason)
    
    def save_account_storage_state(self, name: str, storage_state: dict):
        """Sauvegarde l'état de session d'un compte (JSON)."""
        import json
        account_id = self.ensure_account_exists(name)
        storage_json = json.dumps(storage_state)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE accounts 
                SET storage_state = ?, updated_at = ?
                WHERE id = ?
            """, (storage_json, datetime.now().isoformat(), account_id))
    
    def get_account_block_info(self, name: str) -> Optional[Dict]:
        """Récupère les informations de blocage d'un compte."""
        account = self.get_account(name)
        if not account or account['status'] != 'temporarily_blocked':
            return None
        
        from datetime import datetime
        now = datetime.now()
        cooldown_until = account.get('cooldown_until')
        
        can_resume = False
        if cooldown_until:
            try:
                until_dt = datetime.fromisoformat(cooldown_until)
                can_resume = now >= until_dt
            except:
                can_resume = True
        
        return {
            'status': account['status'],
            'reason': account.get('status_reason'),
            'until': cooldown_until,
            'can_resume': can_resume
        }
    
    def record_account_block(self, name: str, block_type: str, reason: str):
        """Enregistre un blocage de compte en DB."""
        account_id = self.ensure_account_exists(name)
        self.set_account_status(account_id, "temporarily_blocked", reason)
        # Enregistrer dans la table account_blocks
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO account_blocks (account_id, block_type, reason, blocked_at)
                VALUES (?, ?, ?, ?)
            """, (account_id, block_type, reason, datetime.now().isoformat()))
    
    # ==================== GROUPS ====================
    
    def add_group(self, url: str, name: str = None, category: str = None, 
                  language: str = "fr", members_count: int = None) -> int:
        """Ajoute ou met à jour un groupe."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Vérifier si existe déjà
            cursor.execute("SELECT id FROM groups WHERE url = ?", (url,))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE groups SET name = COALESCE(?, name), 
                                      category = COALESCE(?, category),
                                      language = COALESCE(?, language),
                                      members_count = COALESCE(?, members_count)
                    WHERE url = ?
                """, (name, category, language, members_count, url))
                return existing[0]
            else:
                cursor.execute("""
                    INSERT INTO groups (url, name, category, language, members_count)
                    VALUES (?, ?, ?, ?, ?)
                """, (url, name, category, language, members_count))
                return cursor.lastrowid
    
    def get_group(self, group_id: int) -> Optional[Dict]:
        """Récupère un groupe par son ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_group_by_url(self, url: str) -> Optional[Dict]:
        """Récupère un groupe par son URL."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM groups WHERE url = ?", (url,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_group_score(self, group_id: int, quality_score: int):
        """Met à jour le score de qualité d'un groupe."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE groups SET quality_score = ? WHERE id = ?
            """, (quality_score, group_id))
    
    def get_best_groups(self, limit: int = 10, category: str = None) -> List[Dict]:
        """Récupère les meilleurs groupes par score de qualité."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if category:
                cursor.execute("""
                    SELECT * FROM groups 
                    WHERE category = ?
                    ORDER BY quality_score DESC, successful_posts DESC
                    LIMIT ?
                """, (category, limit))
            else:
                cursor.execute("""
                    SELECT * FROM groups 
                    ORDER BY quality_score DESC, successful_posts DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_groups(self) -> List[Dict]:
        """Récupère tous les groupes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM groups ORDER BY quality_score DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== PUBLICATIONS ====================
    
    def record_publication(self, account_id: int, group_id: int, 
                          campaign_name: str = None, variant_id: str = None,
                          text_content: str = None, images: List[str] = None,
                          status: str = "success", error_message: str = None,
                          screenshot_path: str = None) -> int:
        """Enregistre une publication."""
        images_json = json.dumps(images) if images else None
        now = datetime.now().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insérer la publication
            cursor.execute("""
                INSERT INTO publications 
                (account_id, group_id, campaign_name, variant_id, text_content, 
                 images, status, error_message, screenshot_path, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (account_id, group_id, campaign_name, variant_id, text_content,
                  images_json, status, error_message, screenshot_path, 
                  now if status == "success" else None))
            
            pub_id = cursor.lastrowid
            
            # Mettre à jour les compteurs du groupe
            if status == "success":
                cursor.execute("""
                    UPDATE groups 
                    SET successful_posts = successful_posts + 1,
                        total_posts = total_posts + 1,
                        last_post_date = ?
                    WHERE id = ?
                """, (now, group_id))
            else:
                cursor.execute("""
                    UPDATE groups 
                    SET failed_posts = failed_posts + 1,
                        total_posts = total_posts + 1
                    WHERE id = ?
                """, (group_id,))
            
            # Mettre à jour l'activité du compte (sans nested context)
            if success := (status == "success"):
                cursor.execute("""
                    UPDATE accounts 
                    SET successful_posts = successful_posts + 1,
                        total_posts = total_posts + 1,
                        last_post_date = ?,
                        last_activity_date = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (now, now, now, account_id))
            else:
                cursor.execute("""
                    UPDATE accounts 
                    SET failed_posts = failed_posts + 1,
                        total_posts = total_posts + 1,
                        last_activity_date = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (now, now, account_id))
            
            return pub_id
    
    def get_publications(self, account_id: int = None, group_id: int = None,
                        limit: int = 50) -> List[Dict]:
        """Récupère l'historique des publications."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM publications WHERE 1=1"
            params = []
            
            if account_id:
                query += " AND account_id = ?"
                params.append(account_id)
            if group_id:
                query += " AND group_id = ?"
                params.append(group_id)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== ERRORS ====================
    
    def record_error(self, account_id: int = None, group_id: int = None,
                    error_type: str = None, error_message: str = None,
                    step: str = None, selector_key: str = None,
                    screenshot_path: str = None, html_snapshot_path: str = None):
        """Enregistre une erreur."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO errors 
                (account_id, group_id, error_type, error_message, step, 
                 selector_key, screenshot_path, html_snapshot_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (account_id, group_id, error_type, error_message, step,
                  selector_key, screenshot_path, html_snapshot_path))
    
    def get_recent_errors(self, limit: int = 20) -> List[Dict]:
        """Récupère les erreurs récentes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM errors 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== SELECTOR STATS ====================
    
    def record_selector_attempt(self, selector_key: str, success: bool,
                               used_selector: str = None, failure_reason: str = None):
        """Enregistre une tentative de sélecteur."""
        now = datetime.now().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Vérifier si existe
            cursor.execute("SELECT id FROM selector_stats WHERE selector_key = ?", 
                          (selector_key,))
            existing = cursor.fetchone()
            
            if existing:
                # Mettre à jour
                if success:
                    cursor.execute("""
                        UPDATE selector_stats 
                        SET successful_attempts = successful_attempts + 1,
                            total_attempts = total_attempts + 1,
                            last_success_date = ?,
                            working_selector = COALESCE(?, working_selector),
                            updated_at = ?
                        WHERE selector_key = ?
                    """, (now, used_selector, now, selector_key))
                else:
                    cursor.execute("""
                        UPDATE selector_stats 
                        SET failed_attempts = failed_attempts + 1,
                            total_attempts = total_attempts + 1,
                            last_failure_date = ?,
                            last_failure_reason = COALESCE(?, last_failure_reason),
                            updated_at = ?
                        WHERE selector_key = ?
                    """, (now, failure_reason, now, selector_key))
                
                # Recalculer le taux de succès
                cursor.execute("""
                    UPDATE selector_stats 
                    SET success_rate = (successful_attempts * 100.0 / total_attempts)
                    WHERE selector_key = ?
                """, (selector_key,))
            else:
                # Créer nouvelle entrée
                cursor.execute("""
                    INSERT INTO selector_stats 
                    (selector_key, working_selector, total_attempts, 
                     successful_attempts, failed_attempts, success_rate,
                     last_success_date, last_failure_date, last_failure_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (selector_key, used_selector if success else None,
                      1, 1 if success else 0, 0 if success else 1,
                      100.0 if success else 0.0,
                      now if success else None,
                      now if not success else None,
                      failure_reason if not success else None))
    
    def get_selector_stats(self) -> List[Dict]:
        """Récupère les statistiques de tous les sélecteurs."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM selector_stats ORDER BY success_rate ASC")
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== REPORTING ====================
    
    def get_dashboard_stats(self) -> Dict:
        """Récupère les statistiques pour le dashboard."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Comptes
            cursor.execute("SELECT COUNT(*) FROM accounts")
            stats["total_accounts"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM accounts WHERE status = 'healthy'")
            stats["healthy_accounts"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM accounts WHERE status = 'temporarily_blocked'")
            stats["blocked_accounts"] = cursor.fetchone()[0]
            
            # Groups
            cursor.execute("SELECT COUNT(*) FROM groups")
            stats["total_groups"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(quality_score) FROM groups")
            stats["avg_group_score"] = round(cursor.fetchone()[0] or 0, 1)
            
            # Publications aujourd'hui
            today = datetime.now().date().isoformat()
            cursor.execute("""
                SELECT COUNT(*) FROM publications WHERE DATE(created_at) = ?
            """, (today,))
            stats["posts_today"] = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM publications 
                WHERE DATE(created_at) = ? AND status = 'success'
            """, (today,))
            stats["successful_posts_today"] = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM publications 
                WHERE DATE(created_at) = ? AND status = 'failed'
            """, (today,))
            stats["failed_posts_today"] = cursor.fetchone()[0]
            
            # Taux de réussite
            if stats["posts_today"] > 0:
                stats["success_rate_today"] = round(
                    stats["successful_posts_today"] * 100 / stats["posts_today"], 1
                )
            else:
                stats["success_rate_today"] = 0
            
            # Erreurs récentes
            cursor.execute("""
                SELECT COUNT(*) FROM errors 
                WHERE DATE(created_at) = DATE('now')
            """)
            stats["errors_today"] = cursor.fetchone()[0]
            
            return stats
    
    def export_account_report(self, account_id: int) -> Dict:
        """Exporte un rapport complet pour un compte."""
        account = self.get_account_by_id(account_id)
        if not account:
            return None
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Publications récentes
            cursor.execute("""
                SELECT * FROM publications 
                WHERE account_id = ? 
                ORDER BY created_at DESC 
                LIMIT 50
            """, (account_id,))
            recent_posts = [dict(row) for row in cursor.fetchall()]
            
            # Erreurs récentes
            cursor.execute("""
                SELECT * FROM errors 
                WHERE account_id = ? 
                ORDER BY created_at DESC 
                LIMIT 20
            """, (account_id,))
            recent_errors = [dict(row) for row in cursor.fetchall()]
            
            # Blocages
            cursor.execute("""
                SELECT * FROM account_blocks 
                WHERE account_id = ? 
                ORDER BY started_at DESC 
                LIMIT 10
            """, (account_id,))
            blocks = [dict(row) for row in cursor.fetchall()]
            
            return {
                "account": account,
                "recent_posts": recent_posts,
                "recent_errors": recent_errors,
                "blocks": blocks,
                "stats": {
                    "total_posts": len(recent_posts),
                    "success_rate": round(
                        sum(1 for p in recent_posts if p["status"] == "success") * 100 / len(recent_posts), 1
                    ) if recent_posts else 0
                }
            }


# Instance globale
_db_instance = None


def get_database() -> BONDatabase:
    """Retourne l'instance globale de la base de données."""
    global _db_instance
    if _db_instance is None:
        _db_instance = BONDatabase()
    return _db_instance


if __name__ == "__main__":
    # Test/demo
    db = BONDatabase()
    
    print("Initialisation de la base de données...")
    print(f"Base créée: {db.db_path}")
    
    # Créer un compte test
    account_id = db.create_account("test_account", "test@example.com")
    print(f"Compte créé: ID {account_id}")
    
    # Ajouter un groupe test
    group_id = db.add_group(
        "https://facebook.com/groups/test/",
        name="Test Group",
        category="agriculture",
        members_count=5000
    )
    print(f"Groupe ajouté: ID {group_id}")
    
    # Enregistrer une publication
    pub_id = db.record_publication(
        account_id=account_id,
        group_id=group_id,
        campaign_name="farmoos",
        status="success"
    )
    print(f"Publication enregistrée: ID {pub_id}")
    
    # Stats dashboard
    stats = db.get_dashboard_stats()
    print("\n=== Dashboard Stats ===")
    for key, value in stats.items():
        print(f"{key}: {value}")
