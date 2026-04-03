"""
human_behavior.py v14 — Anti-détection avancé : comportement humain

PHASE 3 : Anti-détection avancé
  - Délais aléatoires entre actions
  - Simulation mouvements souris
  - Scroll avant actions
  - Positions de clic randomisées
  - Patterns temporels non-linéaires (courbe de Bézier, distribution Gamma)

Principes :
  • Aucun timing fixe ou linéaire → impossible à fingerprinter
  • Variabilité simulant la fatigue humaine (ralentissement progressif)
  • Trajectoires souris organiques (Bézier cubic)
  • Micro-pauses naturelles intra-action
"""

import math
import random
import time
from typing import Optional, Tuple, List


# ── Distributions de timing non-linéaires ─────────────────────────────────────

def _gamma_delay(mean: float, variance_ratio: float = 0.3) -> float:
    """
    Génère un délai suivant une distribution Gamma.

    La distribution Gamma est naturelle pour les temps de réaction humains :
    légèrement asymétrique à droite, pas de valeur nulle possible.

    mean           : temps moyen en secondes
    variance_ratio : écart-type / moyenne (0.3 = 30% de variance)
    """
    k = 1.0 / (variance_ratio ** 2)   # shape parameter
    theta = mean / k                    # scale parameter
    return random.gammavariate(k, theta)


def _bezier_point(t: float, p0: float, p1: float, p2: float, p3: float) -> float:
    """Courbe de Bézier cubique pour une coordonnée."""
    mt = 1 - t
    return (mt**3 * p0 +
            3 * mt**2 * t * p1 +
            3 * mt * t**2 * p2 +
            t**3 * p3)


def _human_typing_delay() -> float:
    """
    Délai entre frappes clavier.
    Bimodale : frappe rapide (80ms) + pauses de réflexion (200-400ms).
    """
    if random.random() < 0.12:           # 12% du temps : pause de réflexion
        return random.uniform(0.18, 0.45)
    # Frappe normale : Gamma centré sur 80ms avec variance élevée
    return _gamma_delay(mean=0.08, variance_ratio=0.5)


def _fatigue_multiplier(actions_done: int) -> float:
    """
    Simule la fatigue : les actions ralentissent progressivement.
    Modèle logarithmique : +20% après 50 actions, +40% après 200.
    """
    if actions_done <= 0:
        return 1.0
    return 1.0 + 0.08 * math.log1p(actions_done / 10)


# ── API publique de délais ─────────────────────────────────────────────────────

def think_delay(min_s: float = 0.5, max_s: float = 2.5,
                actions_done: int = 0) -> None:
    """
    Pause de 'réflexion' avant une action importante.
    Non-linéaire + facteur fatigue.
    """
    base = _gamma_delay(mean=(min_s + max_s) / 2, variance_ratio=0.35)
    base = max(min_s, min(max_s * 1.5, base))
    base *= _fatigue_multiplier(actions_done)
    time.sleep(base)


def micro_delay() -> None:
    """Micro-pause intra-action (0–120ms). Simule latence de traitement humain."""
    time.sleep(_gamma_delay(mean=0.04, variance_ratio=0.8))


def page_read_delay(content_length_estimate: int = 500) -> None:
    """
    Pause de lecture de page, proportionnelle au contenu estimé.
    ~200 mots/minute en lecture normale.

    content_length_estimate : longueur approximative du texte visible
    """
    words = content_length_estimate / 5          # 5 chars/mot en moyenne
    reading_time = words / 200 * 60             # secondes
    # Limité entre 1s et 15s, avec variance 40%
    reading_time = max(1.0, min(15.0, reading_time))
    actual = _gamma_delay(mean=reading_time, variance_ratio=0.4)
    time.sleep(max(0.8, actual))


def between_actions_delay(base_min: float = 1.0, base_max: float = 4.0,
                          actions_done: int = 0) -> None:
    """
    Délai principal entre deux actions (post, commentaire, rejoindre...).
    Non-linéaire. Inclut facteur fatigue.
    """
    mean = (base_min + base_max) / 2
    delay = _gamma_delay(mean=mean, variance_ratio=0.4)
    delay = max(base_min * 0.7, min(base_max * 2.0, delay))
    delay *= _fatigue_multiplier(actions_done)
    time.sleep(delay)


def post_action_delay() -> None:
    """Délai post-action (attente résultat). 0.3–1.2s non-linéaire."""
    time.sleep(_gamma_delay(mean=0.6, variance_ratio=0.5))


# ── Simulation souris ──────────────────────────────────────────────────────────

def _generate_bezier_path(
    start: Tuple[float, float],
    end: Tuple[float, float],
    n_points: int = 20,
) -> List[Tuple[float, float]]:
    """
    Génère une trajectoire souris organique via Bézier cubique.

    Les points de contrôle sont légèrement aléatoires pour éviter
    des mouvements mécaniquement droits.
    """
    x0, y0 = start
    x1, y1 = end

    # Points de contrôle avec déviation aléatoire
    dx = x1 - x0
    dy = y1 - y0

    # Contrôle 1 : 1/3 du chemin + légère déviation perpendiculaire
    cp1x = x0 + dx * 0.33 + random.uniform(-abs(dx) * 0.15, abs(dx) * 0.15)
    cp1y = y0 + dy * 0.33 + random.uniform(-abs(dy) * 0.20, abs(dy) * 0.20)

    # Contrôle 2 : 2/3 du chemin + légère déviation
    cp2x = x0 + dx * 0.66 + random.uniform(-abs(dx) * 0.15, abs(dx) * 0.15)
    cp2y = y0 + dy * 0.66 + random.uniform(-abs(dy) * 0.20, abs(dy) * 0.20)

    points = []
    for i in range(n_points + 1):
        t = i / n_points
        px = _bezier_point(t, x0, cp1x, cp2x, x1)
        py = _bezier_point(t, y0, cp1y, cp2y, y1)
        points.append((px, py))

    return points


async def simulate_mouse_move_async(page, start: Tuple[float, float],
                                    end: Tuple[float, float]) -> None:
    """Version async pour Playwright async API."""
    path = _generate_bezier_path(start, end, n_points=random.randint(15, 25))
    for px, py in path:
        await page.mouse.move(px, py)
        await page.wait_for_timeout(random.randint(5, 20))


def simulate_mouse_move(page, start: Tuple[float, float],
                        end: Tuple[float, float]) -> None:
    """
    Simule un déplacement souris humain (Playwright sync API).

    Trajectoire Bézier cubique avec vitesse variable.
    Plus lent en début/fin (profil de vitesse en cloche).
    """
    path = _generate_bezier_path(start, end, n_points=random.randint(15, 25))
    n = len(path)
    for i, (px, py) in enumerate(path):
        page.mouse.move(px, py)
        # Vitesse non-uniforme : ralentissement en début et fin
        # Profil sinusoïdal : v(t) ∝ sin(π·t)
        t = i / max(n - 1, 1)
        speed_factor = math.sin(math.pi * t) + 0.1  # évite div/0
        delay_ms = int(15 / speed_factor)
        delay_ms = max(5, min(40, delay_ms))
        time.sleep(delay_ms / 1000)


def randomize_click_position(element_box: dict,
                              margin_ratio: float = 0.25) -> Tuple[float, float]:
    """
    Randomise la position de clic dans un élément DOM.

    Au lieu de toujours cliquer au centre (détectable), clic dans une zone
    aléatoire à l'intérieur de l'élément (évitant les bords à margin_ratio%).

    element_box : {"x": float, "y": float, "width": float, "height": float}
    """
    x = element_box["x"]
    y = element_box["y"]
    w = element_box["width"]
    h = element_box["height"]

    margin_x = w * margin_ratio
    margin_y = h * margin_ratio

    # Distribution Bêta légèrement centrée (évite les bords)
    # betavariate(2, 2) est en cloche centrée sur 0.5
    rx = random.betavariate(2, 2)
    ry = random.betavariate(2, 2)

    click_x = x + margin_x + rx * (w - 2 * margin_x)
    click_y = y + margin_y + ry * (h - 2 * margin_y)

    return click_x, click_y


def human_click(page, selector: str, actions_done: int = 0) -> bool:
    """
    Clic humain complet sur un élément :
      1. Scroll vers l'élément
      2. Déplacement souris depuis position actuelle
      3. Micro-pause
      4. Clic sur position randomisée
      5. Post-action delay

    Retourne True si succès.
    """
    try:
        element = page.query_selector(selector)
        if not element:
            return False

        # 1. Scroll vers l'élément
        element.scroll_into_view_if_needed()
        time.sleep(_gamma_delay(mean=0.3, variance_ratio=0.4))

        # 2. Obtenir la position de l'élément
        box = element.bounding_box()
        if not box:
            element.click()
            return True

        # 3. Déplacement souris depuis position aléatoire proche
        current_x = random.uniform(box["x"] - 200, box["x"] + box["width"] + 200)
        current_y = random.uniform(box["y"] - 150, box["y"] + box["height"] + 150)
        current_x = max(0, min(current_x, 1280))
        current_y = max(0, min(current_y, 720))

        simulate_mouse_move(page,
                            start=(current_x, current_y),
                            end=(box["x"] + box["width"] / 2,
                                 box["y"] + box["height"] / 2))

        # 4. Micro-pause avant clic
        micro_delay()

        # 5. Clic sur position randomisée
        click_x, click_y = randomize_click_position(box)
        page.mouse.click(click_x, click_y)

        # 6. Post-action
        post_action_delay()
        return True

    except Exception:
        # Fallback : clic standard
        try:
            page.click(selector)
            post_action_delay()
            return True
        except Exception:
            return False


# ── Scroll humain ──────────────────────────────────────────────────────────────

def human_scroll(page, direction: str = "down",
                 distance_px: Optional[int] = None) -> None:
    """
    Scroll humain : mouvements courts et rapides, non-linéaires.

    direction    : 'down' | 'up'
    distance_px  : si None, distance aléatoire entre 300 et 800px
    """
    if distance_px is None:
        distance_px = random.randint(300, 800)

    sign = 1 if direction == "down" else -1

    # Scroll en plusieurs petits mouvements (simule molette)
    n_moves = random.randint(3, 8)
    remaining = distance_px

    for i in range(n_moves):
        chunk = remaining // (n_moves - i) if i < n_moves - 1 else remaining
        chunk += random.randint(-30, 30)
        chunk = max(50, chunk)

        page.mouse.wheel(0, sign * chunk)
        remaining -= chunk

        # Délai entre mouvements de molette (30-120ms)
        time.sleep(random.uniform(0.03, 0.12))

    # Pause après scroll (l'humain regarde ce qu'il vient de scroller)
    time.sleep(_gamma_delay(mean=0.8, variance_ratio=0.5))


def scroll_before_action(page, target_selector: Optional[str] = None) -> None:
    """
    Scroll naturel avant une action importante.
    Simule la lecture de la page avant d'agir.
    """
    if target_selector:
        try:
            page.query_selector(target_selector)
        except Exception:
            pass

    # 1-3 scrolls avant d'agir
    n = random.randint(1, 3)
    for _ in range(n):
        distance = random.randint(150, 500)
        human_scroll(page, direction="down", distance_px=distance)
        time.sleep(_gamma_delay(mean=1.2, variance_ratio=0.4))


def human_type(page, selector: str, text: str) -> bool:
    """
    Frappe clavier humaine : délais variables entre touches.
    Inclut erreurs de frappe occasionnelles avec correction.
    """
    try:
        element = page.query_selector(selector)
        if not element:
            return False

        element.click()
        time.sleep(_gamma_delay(mean=0.3, variance_ratio=0.5))

        for char in text:
            # Erreur de frappe simulée (3% chance)
            if random.random() < 0.03 and char.isalpha():
                wrong_char = random.choice("qwertyuiopasdfghjklzxcvbnm")
                page.keyboard.type(wrong_char)
                time.sleep(_human_typing_delay())
                page.keyboard.press("Backspace")
                time.sleep(_gamma_delay(mean=0.15, variance_ratio=0.4))

            page.keyboard.type(char)
            time.sleep(_human_typing_delay())

        return True
    except Exception:
        return False
