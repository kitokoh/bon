"""
diagnostic.py — v2
"""
import sys, os, pathlib

print("\n=== DIAGNOSTIC BON v2 ===\n")

here = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(here))

# Où Python trouve-t-il 'libs' ?
print("--- Recherche de 'libs' dans sys.path ---")
for p in sys.path:
    candidate = pathlib.Path(p) / 'libs'
    if candidate.exists():
        print(f"  TROUVÉ : {candidate}")
        print(f"    config_manager.py présent : {(candidate / 'config_manager.py').exists()}")

print()

# Quel 'libs' Python choisit-il réellement ?
try:
    import libs
    print(f"libs importé depuis : {libs.__file__ or libs.__path__}")
except Exception as e:
    print(f"import libs échoué : {e}")

# Y a-t-il un libs dans .venv ?
venv = here / '.venv'
if venv.exists():
    for f in venv.rglob('libs'):
        if f.is_dir():
            print(f"\n⚠️  libs trouvé dans .venv : {f}")

print("\n=== FIN ===\n")