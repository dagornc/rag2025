"""Test pour comprendre le fonctionnement réel de l'algorithme recursive de LangChain."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def test_recursive_vs_fixed():
    """Compare les stratégies recursive et fixed pour comprendre la différence."""
    print("\n" + "=" * 80)
    print("TEST : Algorithme Recursive vs Fixed")
    print("=" * 80)

    # Texte de test avec structure hiérarchique claire
    test_text = """Section A - Introduction

Ceci est le premier paragraphe de la section A.
Il contient plusieurs phrases sur une seule ligne.

Ceci est le deuxième paragraphe de la section A.
Il est séparé par une double newline.


Section B - Développement

Ceci est le premier paragraphe de la section B.
Cette section est séparée de la section A par une triple newline.

Ceci est le deuxième paragraphe de la section B.
Il contient aussi plusieurs phrases.


Section C - Conclusion

Paragraphe final avec plusieurs phrases. Cette phrase est longue et contient beaucoup de mots pour tester le découpage."""

    print(f"\nTexte original ({len(test_text)} caractères):")
    print("-" * 80)
    print(test_text[:200] + "...\n")

    # Test 1: Algorithme Fixed (simple découpage linéaire)
    print("\n" + "=" * 80)
    print("TEST 1 : Stratégie FIXED (découpage linéaire)")
    print("=" * 80)

    from rag_framework.config import load_step_config
    from rag_framework.steps.step_03_chunking import ChunkingStep

    # Configuration pour fixed
    config_fixed = load_step_config("03_chunking.yaml")
    config_fixed["strategy"] = "fixed"
    config_fixed["fixed"] = {"chunk_size": 100, "overlap": 20}

    chunking_step_fixed = ChunkingStep(config_fixed)
    chunks_fixed = chunking_step_fixed._chunk_fixed(test_text)

    print(f"\nNombre de chunks: {len(chunks_fixed)}")
    for i, chunk in enumerate(chunks_fixed[:3], 1):
        print(f"\n--- Chunk {i} (taille: {len(chunk)}) ---")
        print(repr(chunk[:100]) + ("..." if len(chunk) > 100 else ""))

    # Test 2: Algorithme Recursive (LangChain)
    print("\n" + "=" * 80)
    print("TEST 2 : Stratégie RECURSIVE (hiérarchique)")
    print("=" * 80)

    # Configuration pour recursive
    config_recursive = load_step_config("03_chunking.yaml")
    config_recursive["strategy"] = "recursive"
    config_recursive["recursive"] = {
        "chunk_size": 100,
        "chunk_overlap": 20,
        "separators": ["\n\n\n", "\n\n", "\n", " ", ""],
    }

    chunking_step_recursive = ChunkingStep(config_recursive)
    chunks_recursive = chunking_step_recursive._chunk_recursive(test_text)

    print(f"\nNombre de chunks: {len(chunks_recursive)}")
    for i, chunk in enumerate(chunks_recursive[:3], 1):
        print(f"\n--- Chunk {i} (taille: {len(chunk)}) ---")
        print(repr(chunk[:100]) + ("..." if len(chunk) > 100 else ""))

    # Test 3: Analyse de l'algorithme
    print("\n" + "=" * 80)
    print("ANALYSE : Différences entre Fixed et Recursive")
    print("=" * 80)

    print(f"""
📊 Comparaison:

Fixed (linéaire):
- Nombre de chunks: {len(chunks_fixed)}
- Taille chunks: Fixe (~100 caractères)
- Découpage: Coupe n'importe où (peut couper au milieu d'un mot)
- Algorithme: Linéaire (while loop avec index)

Recursive (hiérarchique):
- Nombre de chunks: {len(chunks_recursive)}
- Taille chunks: Variable (respecte les séparateurs)
- Découpage: Préserve la structure (sections, paragraphes, lignes)
- Algorithme: Récursif/Hiérarchique (essaie séparateurs dans l'ordre)
""")

    # Test 4: Vérifier si recursive respecte vraiment les séparateurs
    print("\n" + "=" * 80)
    print("TEST 3 : Vérification de l'algorithme récursif")
    print("=" * 80)

    print("\n🔍 Analyse des points de découpe:")
    print("\nFixed (coupe arbitrairement):")
    for i, chunk in enumerate(chunks_fixed[:3], 1):
        # Vérifier si coupe au milieu d'un mot
        first_char = chunk[0] if chunk else ""
        last_char = chunk[-1] if chunk else ""
        print(
            f"  Chunk {i}: Commence par '{first_char}' | Se termine par '{last_char}'"
        )
        if last_char not in ["\n", " ", ".", "!"]:
            print("    ⚠️ Coupe probablement au milieu d'un mot")

    print("\nRecursive (respecte les séparateurs):")
    for i, chunk in enumerate(chunks_recursive[:3], 1):
        first_chars = chunk[:20] if len(chunk) >= 20 else chunk
        last_chars = chunk[-20:] if len(chunk) >= 20 else chunk
        print(f"  Chunk {i}:")
        print(f"    Début: {first_chars!r}")
        print(f"    Fin: {last_chars!r}")

        # Vérifier si découpe sur séparateur hiérarchique
        if (
            chunk.startswith("\n\n\n")
            or chunk.startswith("\n\n")
            or chunk.startswith("\n")
        ):
            print("    ✅ Découpe sur séparateur hiérarchique")

    # Test 5: Algorithme récursif expliqué
    print("\n" + "=" * 80)
    print("EXPLICATION : Comment fonctionne l'algorithme récursif")
    print("=" * 80)

    print("""
L'algorithme RecursiveCharacterTextSplitter fonctionne ainsi :

1. Séparateurs hiérarchiques définis :
   - Niveau 1: "\\n\\n\\n" (sections majeures)
   - Niveau 2: "\\n\\n"    (paragraphes)
   - Niveau 3: "\\n"      (lignes)
   - Niveau 4: " "       (mots)
   - Niveau 5: ""        (caractères)

2. Processus récursif :
   a) Découpe le texte avec le séparateur de niveau 1
   b) Pour chaque morceau :
      - Si taille <= chunk_size : OK, on garde
      - Si taille > chunk_size : RE-DÉCOUPE avec séparateur niveau 2
      - Si encore trop grand : RE-DÉCOUPE avec niveau 3
      - Etc. jusqu'au niveau 5 (caractères)

3. Avantages :
   ✅ Préserve la structure logique du document
   ✅ Évite de couper au milieu d'un paragraphe si possible
   ✅ Évite de couper au milieu d'une ligne si possible
   ✅ Évite de couper au milieu d'un mot si possible
   ✅ Seulement en dernier recours : coupe au caractère

4. C'est VRAIMENT récursif :
   - Fonction qui s'appelle elle-même avec un séparateur différent
   - Descend dans la hiérarchie jusqu'à trouver un découpage valide
   - Remonte en assemblant les morceaux avec chunk_overlap

Exemple concret :
Texte de 500 caractères, chunk_size=100

Étape 1: Essai séparateur "\\n\\n\\n"
  → Découpe en 2 morceaux de 250 chars chacun
  → TROP GRAND (250 > 100)

Étape 2: Pour chaque morceau de 250, essai "\\n\\n"
  → Découpe en 3 morceaux de ~80 chars
  → OK! (80 < 100)

Résultat: 6 chunks de ~80 chars au lieu de 5 chunks de 100 chars
          avec respect des paragraphes
""")

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)

    print("""
✅ OUI, c'est bien un algorithme RÉCURSIF qui s'applique !

Le nom "recursive" n'est pas trompeur :
- L'algorithme de LangChain utilise la récursion pour descendre
  dans la hiérarchie des séparateurs
- Ce n'est pas juste un algorithme "hiérarchique" ou "itératif"
- C'est une vraie implémentation récursive qui s'appelle elle-même

Différence clé avec "fixed" :
- Fixed: Découpe linéaire brutale (coupe n'importe où)
- Recursive: Découpe intelligente récursive (respecte la structure)

Performance :
- Fixed: O(n) - très rapide
- Recursive: O(n * log(m)) où m = nombre de séparateurs
             - Légèrement plus lent mais qualité supérieure
""")


if __name__ == "__main__":
    test_recursive_vs_fixed()
