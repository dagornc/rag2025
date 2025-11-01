"""Test des stratégies de chunking."""

import sys
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from rag_framework.config import load_step_config
from rag_framework.steps.step_03_chunking import ChunkingStep


def test_strategy(strategy_name: str) -> None:
    """Teste une stratégie de chunking.

    Parameters
    ----------
    strategy_name : str
        Nom de la stratégie à tester (recursive, semantic, fixed, llm_guided).
    """
    print(f"\n{'=' * 70}")
    print(f"TEST DE LA STRATÉGIE: {strategy_name.upper()}")
    print(f"{'=' * 70}")

    # Texte de test
    test_text = """
    Le Règlement Général sur la Protection des Données (RGPD) est un règlement
    de l'Union européenne qui constitue le texte de référence en matière de
    protection des données à caractère personnel.

    Le RGPD renforce et unifie la protection des données pour les individus
    au sein de l'Union européenne. Il impose également des règles strictes
    concernant le transfert des données personnelles en dehors de l'UE.

    Les entreprises doivent mettre en œuvre des mesures techniques et
    organisationnelles appropriées pour garantir la sécurité des données.
    Cela inclut le chiffrement, la pseudonymisation et les tests de sécurité
    réguliers.

    En cas de violation de données, les organisations ont l'obligation de
    notifier l'autorité de contrôle compétente dans un délai de 72 heures.
    Les sanctions peuvent aller jusqu'à 20 millions d'euros ou 4% du chiffre
    d'affaires annuel mondial.
    """

    # Charger la configuration
    config = load_step_config("03_chunking.yaml")

    # Modifier la stratégie
    config["strategy"] = strategy_name

    # Activer LLM si nécessaire pour llm_guided
    if strategy_name == "llm_guided":
        config["llm"]["enabled"] = True

    # Créer l'instance de chunking
    try:
        chunking_step = ChunkingStep(config)
        print(f"✓ ChunkingStep initialisé avec stratégie '{strategy_name}'")
    except Exception as e:
        print(f"✗ ERREUR lors de l'initialisation: {e}")
        return

    # Créer un document de test
    test_document = {
        "text": test_text,
        "source_file": "test_rgpd.txt",
        "metadata": {"title": "Test RGPD"},
    }

    # Exécuter le chunking
    try:
        data = {"extracted_documents": [test_document]}
        result = chunking_step.execute(data)
        chunks = result.get("chunks", [])

        print("✓ Chunking exécuté avec succès")
        print(f"  Nombre de chunks créés: {len(chunks)}")

        # Afficher les chunks
        for i, chunk in enumerate(chunks[:3], 1):  # Afficher max 3 chunks
            print(f"\n  Chunk #{i} ({len(chunk['text'])} caractères):")
            preview = chunk["text"][:100].replace("\n", " ")
            print(f"    {preview}...")

        if len(chunks) > 3:
            print(f"\n  ... et {len(chunks) - 3} chunks supplémentaires")

        # Statistiques
        avg_length = sum(len(c["text"]) for c in chunks) / len(chunks) if chunks else 0
        print(f"\n  Longueur moyenne des chunks: {avg_length:.0f} caractères")

    except Exception as e:
        print(f"✗ ERREUR lors de l'exécution: {e}")
        import traceback

        traceback.print_exc()


def main() -> None:
    """Fonction principale."""
    print("\n" + "=" * 70)
    print("TEST DE TOUTES LES STRATÉGIES DE CHUNKING")
    print("=" * 70)

    strategies = ["recursive", "fixed", "semantic", "llm_guided"]

    results = {}
    for strategy in strategies:
        try:
            test_strategy(strategy)
            results[strategy] = "✓ SUCCÈS"
        except Exception as e:
            results[strategy] = f"✗ ÉCHEC: {e}"

    # Résumé final
    print(f"\n{'=' * 70}")
    print("RÉSUMÉ DES TESTS")
    print(f"{'=' * 70}")
    for strategy, result in results.items():
        print(f"{strategy:15} : {result}")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
