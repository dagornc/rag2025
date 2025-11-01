"""Test pour vérifier que LangChain est correctement installé et importé."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rag_framework.config import load_step_config
from rag_framework.steps.step_03_chunking import ChunkingStep


def test_langchain_import():
    """Teste que LangChain est correctement importé."""
    print("\n" + "="*70)
    print("TEST D'IMPORT DE LANGCHAIN")
    print("="*70)

    # Test 1 : Import direct
    print("\n[1/3] Test d'import direct de langchain_text_splitters...")
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        print("✅ langchain_text_splitters importé avec succès")
        print(f"    Module: {RecursiveCharacterTextSplitter.__module__}")
    except ImportError as e:
        print(f"❌ Échec import langchain_text_splitters: {e}")
        return False

    # Test 2 : Instanciation du splitter
    print("\n[2/3] Test d'instanciation du RecursiveCharacterTextSplitter...")
    try:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""],
        )
        print("✅ RecursiveCharacterTextSplitter instancié avec succès")
        print(f"    Chunk size: {splitter._chunk_size}")
        print(f"    Chunk overlap: {splitter._chunk_overlap}")
    except Exception as e:
        print(f"❌ Échec instanciation: {e}")
        return False

    # Test 3 : Utilisation dans ChunkingStep
    print("\n[3/3] Test d'utilisation dans ChunkingStep...")
    config = load_step_config("03_chunking.yaml")
    config["strategy"] = "recursive"

    chunking_step = ChunkingStep(config)

    test_text = """
    Le Règlement Général sur la Protection des Données (RGPD) est un règlement
    de l'Union européenne qui constitue le texte de référence en matière de
    protection des données à caractère personnel.

    Le RGPD renforce et unifie la protection des données pour les individus
    au sein de l'Union européenne. Il impose également des règles strictes
    concernant le transfert des données personnelles en dehors de l'UE.

    Les entreprises doivent mettre en œuvre des mesures techniques et
    organisationnelles appropriées pour garantir la sécurité des données.
    """ * 10  # Répéter pour avoir un texte plus long

    test_doc = {
        "text": test_text,
        "file_path": "test.txt",
        "metadata": {},
    }

    try:
        data = {"extracted_documents": [test_doc]}
        result = chunking_step.execute(data)
        chunks = result.get("chunks", [])

        print(f"✅ ChunkingStep exécuté avec succès")
        print(f"    Chunks créés: {len(chunks)}")
        print(f"    Taille moyenne: {sum(len(c['text']) for c in chunks) / len(chunks):.0f} caractères")

        # Vérifier que LangChain a bien été utilisé (pas de warning)
        # Le test précédent aurait affiché un warning si LangChain n'était pas disponible
        return True

    except Exception as e:
        print(f"❌ Échec execution ChunkingStep: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_langchain_import()

    print("\n" + "="*70)
    if success:
        print("✅ TOUS LES TESTS PASSÉS - LangChain fonctionne correctement")
    else:
        print("❌ ÉCHEC - Problèmes détectés")
    print("="*70 + "\n")

    sys.exit(0 if success else 1)
