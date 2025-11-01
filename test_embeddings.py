"""Test des embeddings avec différents providers."""

import sys
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from rag_framework.config import load_step_config
from rag_framework.steps.step_06_embedding import EmbeddingStep


def test_embedding_provider(provider: str, model: str) -> None:
    """Teste un provider d'embeddings.

    Parameters
    ----------
    provider : str
        Nom du provider (mistral_ai, openai, sentence-transformers, etc.).
    model : str
        Nom du modèle d'embeddings.
    """
    print(f"\n{'='*70}")
    print(f"TEST DU PROVIDER: {provider.upper()}")
    print(f"Modèle: {model}")
    print(f"{'='*70}")

    # Textes de test
    test_texts = [
        "Le Règlement Général sur la Protection des Données (RGPD) est un règlement de l'Union européenne.",
        "La cybersécurité est essentielle pour protéger les systèmes d'information contre les menaces.",
        "L'audit de conformité permet de vérifier le respect des exigences réglementaires.",
    ]

    # Charger la configuration
    config = load_step_config("06_embedding.yaml")

    # Modifier le provider et le modèle
    config["provider"] = provider
    config["model"] = model

    # Créer des chunks enrichis de test
    enriched_chunks = [
        {
            "text": text,
            "chunk_index": i,
            "source_file": "test_rgpd.txt",
            "sensitivity": "confidentiel",
            "document_type": "rapport_conformite",
        }
        for i, text in enumerate(test_texts)
    ]

    # Créer l'instance d'embedding
    try:
        embedding_step = EmbeddingStep(config)
        print(f"✓ EmbeddingStep initialisé avec provider '{provider}'")
    except Exception as e:
        print(f"✗ ERREUR lors de l'initialisation: {e}")
        import traceback
        traceback.print_exc()
        return

    # Exécuter le processus d'embedding
    try:
        data = {"enriched_chunks": enriched_chunks}
        result = embedding_step.execute(data)
        embedded_chunks = result.get("embedded_chunks", [])

        print(f"✓ Embeddings générés avec succès")
        print(f"  Nombre de chunks: {len(embedded_chunks)}")

        if embedded_chunks:
            first_chunk = embedded_chunks[0]
            print(f"\n  Premier chunk:")
            print(f"    Provider: {first_chunk.get('embedding_provider')}")
            print(f"    Modèle: {first_chunk.get('embedding_model')}")
            print(f"    Dimensions: {first_chunk.get('embedding_dimensions')}")
            print(f"    Texte (début): {first_chunk['text'][:80]}...")

            # Afficher un aperçu de l'embedding
            embedding = first_chunk.get("embedding", [])
            if embedding:
                print(f"    Embedding (premiers 10 valeurs): {embedding[:10]}")
                print(f"    Norme L2: {sum(x**2 for x in embedding)**0.5:.4f}")

        # Vérifier la cohérence
        all_same_dim = len(set(c.get("embedding_dimensions") for c in embedded_chunks)) == 1
        if all_same_dim:
            print(f"\n  ✓ Toutes les embeddings ont la même dimension")
        else:
            print(f"\n  ✗ AVERTISSEMENT: Dimensions d'embeddings incohérentes")

    except Exception as e:
        print(f"✗ ERREUR lors de l'exécution: {e}")
        import traceback
        traceback.print_exc()


def main() -> None:
    """Fonction principale."""
    print("\n" + "="*70)
    print("TEST DES EMBEDDINGS - DIFFÉRENTS PROVIDERS")
    print("="*70)

    # Test avec Mistral AI (configuré avec la clé API)
    print("\n" + "-"*70)
    print("Test 1/3 : Mistral AI (API)")
    print("-"*70)
    test_embedding_provider("mistral_ai", "mistral-embed")

    # Test avec embeddings simulés (fallback)
    print("\n" + "-"*70)
    print("Test 2/3 : Embeddings simulés (fallback)")
    print("-"*70)
    # Provider invalide pour forcer le fallback
    test_embedding_provider("simulated", "dummy-model")

    # Test avec OpenAI (nécessite clé API configurée)
    print("\n" + "-"*70)
    print("Test 3/3 : OpenAI (API) - Optionnel")
    print("-"*70)
    print("Note: Ce test nécessite une clé API OpenAI configurée dans global.yaml")
    print("      Ignoré si la clé n'est pas configurée.")

    print("\n" + "="*70)
    print("TESTS TERMINÉS")
    print("="*70)


if __name__ == "__main__":
    main()
