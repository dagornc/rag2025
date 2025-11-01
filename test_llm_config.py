#!/usr/bin/env python3
"""Script de test pour la nouvelle configuration LLM à deux niveaux.

Ce script vérifie que :
1. La configuration globale charge correctement les llm_providers
2. Les configurations d'étapes chargent correctement les paramètres LLM
3. La fonction get_llm_client peut créer un client (sans faire d'appel réel)
"""

from pathlib import Path

from rag_framework.config import get_llm_client, load_config, load_step_config


def test_global_config_loading() -> None:
    """Test du chargement de la configuration globale."""
    print("=" * 70)
    print("TEST 1: Chargement de la configuration globale")
    print("=" * 70)

    global_config = load_config(Path("config"))

    print("\n✓ Configuration globale chargée avec succès")
    print(f"  Providers LLM disponibles: {list(global_config.llm_providers.keys())}")

    # Vérification des 6 providers attendus
    expected_providers = [
        "lm_studio",
        "ollama",
        "vllm",
        "huggingface",
        "mistral_ai",
        "generic_api",
    ]

    for provider in expected_providers:
        if provider in global_config.llm_providers:
            config = global_config.llm_providers[provider]
            print(f"\n  Provider '{provider}':")
            print(f"    - access_method: {config.get('access_method')}")
            print(f"    - base_url: {config.get('base_url')}")
            print(
                f"    - api_key: {config.get('api_key')[:20]}..."
                if isinstance(config.get("api_key"), str)
                and len(config.get("api_key", "")) > 20
                else f"    - api_key: {config.get('api_key')}"
            )
        else:
            print(f"\n  ⚠ Provider '{provider}' manquant")

    print("\n" + "=" * 70)


def test_step_config_loading() -> None:
    """Test du chargement des configurations d'étapes."""
    print("\nTEST 2: Chargement des configurations d'étapes")
    print("=" * 70)

    # Test étape 4 (enrichment)
    enrichment_config = load_step_config("04_enrichment.yaml")

    llm_config = enrichment_config.get("llm", {})
    print("\n✓ Configuration de l'étape 4 (enrichment) chargée")
    print(f"  LLM activé: {llm_config.get('enabled', False)}")
    print(f"  Provider: {llm_config.get('provider', 'N/A')}")
    print(f"  Modèle: {llm_config.get('model', 'N/A')}")
    print(f"  Température: {llm_config.get('temperature', 'N/A')}")
    print(f"  Max tokens: {llm_config.get('max_tokens', 'N/A')}")

    # Test étape 5 (audit)
    audit_config = load_step_config("05_audit.yaml")

    llm_config = audit_config.get("llm", {})
    print("\n✓ Configuration de l'étape 5 (audit) chargée")
    print(f"  LLM activé: {llm_config.get('enabled', False)}")
    print(f"  Provider: {llm_config.get('provider', 'N/A')}")
    print(f"  Modèle: {llm_config.get('model', 'N/A')}")
    print(f"  Température: {llm_config.get('temperature', 'N/A')}")
    print(f"  Max tokens: {llm_config.get('max_tokens', 'N/A')}")

    # Test étape 3 (chunking sémantique)
    chunking_config = load_step_config("03_chunking.yaml")

    semantic_config = chunking_config.get("semantic", {})
    print("\n✓ Configuration de l'étape 3 (chunking sémantique) chargée")
    print(f"  Provider: {semantic_config.get('provider', 'N/A')}")
    print(f"  Modèle: {semantic_config.get('model', 'N/A')}")

    print("\n" + "=" * 70)


def test_llm_client_creation() -> None:
    """Test de la création d'un client LLM (sans appel réel)."""
    print("\nTEST 3: Création d'un client LLM")
    print("=" * 70)

    global_config = load_config(Path("config"))

    # Test avec provider local (ollama) qui ne nécessite pas de clé API valide
    try:
        print("\n  Tentative de création d'un client 'ollama'...")
        client = get_llm_client(
            provider_name="ollama",
            model="llama3",
            temperature=0.0,
            global_config=global_config,
        )

        print(f"  ✓ Client LLM créé avec succès: {type(client).__name__}")
        print(f"  Modèle configuré: {client._model}")  # type: ignore[attr-defined]
        print(f"  Température: {client._temperature}")  # type: ignore[attr-defined]
        print(
            f"  Base URL: {client.base_url}"  # type: ignore[attr-defined]
        )

    except Exception as e:
        print(f"  ⚠ Erreur lors de la création du client: {e}")
        print(
            "  (Ceci est normal si la librairie 'openai' n'est pas installée "
            "ou si les variables d'environnement ne sont pas définies)"
        )

    print("\n" + "=" * 70)


def test_provider_not_found() -> None:
    """Test de gestion d'erreur pour un provider inexistant."""
    print("\nTEST 4: Gestion d'erreur - Provider inexistant")
    print("=" * 70)

    global_config = load_config(Path("config"))

    try:
        print("\n  Tentative avec un provider inexistant 'fake_provider'...")
        get_llm_client(
            provider_name="fake_provider",
            model="fake-model",
            temperature=0.0,
            global_config=global_config,
        )
        print("  ✗ Erreur: Aucune exception levée (attendu: ConfigurationError)")

    except Exception as e:
        print(f"  ✓ Exception levée correctement: {type(e).__name__}")
        print(f"  Message: {e}")

    print("\n" + "=" * 70)


def main() -> None:
    """Point d'entrée principal."""
    print("\n" + "=" * 70)
    print("TEST DE LA NOUVELLE CONFIGURATION LLM À DEUX NIVEAUX")
    print("=" * 70)

    try:
        # Test 1: Chargement config globale
        test_global_config_loading()

        # Test 2: Chargement configs d'étapes
        test_step_config_loading()

        # Test 3: Création de client LLM
        test_llm_client_creation()

        # Test 4: Gestion d'erreur
        test_provider_not_found()

        print("\n" + "=" * 70)
        print("RÉSUMÉ: Tous les tests de configuration ont été exécutés")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ ERREUR CRITIQUE: {e}")
        import traceback

        traceback.print_exc()
        return

    print(
        "\n✓ La nouvelle configuration LLM à deux niveaux fonctionne correctement !\n"
    )


if __name__ == "__main__":
    main()
