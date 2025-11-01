"""Interface CLI pour le framework RAG."""

import argparse
import signal
import sys
import time
from pathlib import Path

from rag_framework import RAGPipeline
from rag_framework.utils.logger import setup_logger
from rag_framework.utils.secrets import load_env_file


def main() -> None:
    """Point d'entrée principal du CLI."""
    parser = argparse.ArgumentParser(
        description="Framework RAG modulaire pour l'audit et la conformité"
    )

    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("config"),
        help="Répertoire contenant les fichiers de configuration (défaut: config/)",
    )

    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Fichier .env contenant les secrets (défaut: .env)",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Niveau de logging (défaut: INFO)",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Affiche le statut du pipeline",
    )

    parser.add_argument(
        "--watch",
        action="store_true",
        help="Mode surveillance continue - surveille et traite les fichiers en continu",
    )

    parser.add_argument(
        "--watch-interval",
        type=int,
        default=10,
        help="Intervalle entre chaque scan en mode watch (secondes, défaut: 10)",
    )

    args = parser.parse_args()

    # Configuration du logger
    logger = setup_logger(level=args.log_level)

    # Chargement des variables d'environnement
    if args.env_file.exists():
        load_env_file(args.env_file)
        logger.info(f"Variables d'environnement chargées depuis {args.env_file}")

    try:
        # Initialisation du pipeline
        pipeline = RAGPipeline(config_dir=args.config_dir)

        # Affichage du statut
        if args.status:
            status = pipeline.get_status()
            print("\n📊 STATUT DU PIPELINE RAG")
            print("=" * 60)
            print(f"Total d'étapes: {status['total_steps']}")
            print(f"Étapes activées: {status['enabled_steps']}")
            print("\nÉtapes:")
            for step in status["steps"]:
                status_icon = "✓" if step["enabled"] else "✗"
                print(f"  {status_icon} {step['name']}")
            print("=" * 60)
            sys.exit(0)

        # Mode surveillance continue
        if args.watch:
            # Gestionnaire de signal pour arrêt propre (Ctrl+C)
            stop_watch = False

            def signal_handler(sig, frame):  # type: ignore[no-untyped-def]
                nonlocal stop_watch
                logger.info("\n🛑 Arrêt de la surveillance (Ctrl+C détecté)")
                stop_watch = True

            signal.signal(signal.SIGINT, signal_handler)

            logger.info("🔍 Mode surveillance continue activé")
            logger.info(f"Intervalle de scan: {args.watch_interval} secondes")
            logger.info("Appuyez sur Ctrl+C pour arrêter\n")

            iteration = 0
            while not stop_watch:
                iteration += 1
                logger.info(f"{'=' * 60}")
                logger.info(
                    f"📊 Itération {iteration} - Scan des répertoires surveillés"
                )
                logger.info(f"{'=' * 60}")

                try:
                    # Exécution du pipeline
                    result = pipeline.execute()

                    # Affichage du résultat
                    doc_count = len(result.get("extracted_documents", []))

                    # Compter les chunks en fonction de l'étape la plus avancée activée
                    # Ordre de priorité : normalized_chunks > enriched_chunks > chunks
                    if "normalized_chunks" in result:
                        chunk_count = len(result["normalized_chunks"])
                    elif "enriched_chunks" in result:
                        chunk_count = len(result["enriched_chunks"])
                    elif "chunks" in result:
                        chunk_count = len(result["chunks"])
                    else:
                        chunk_count = 0

                    if doc_count > 0:
                        print(f"\n✅ {doc_count} document(s) traité(s)")
                        print(f"📦 {chunk_count} chunk(s) créé(s)")

                        if result.get("storage_result"):
                            storage = result["storage_result"]
                            print(
                                f"💾 {storage.get('stored_count', 0)} chunk(s) stocké(s)"
                            )
                    else:
                        logger.info("Aucun nouveau fichier détecté")

                except Exception as e:
                    logger.error(
                        f"Erreur durant l'itération {iteration}: {e}", exc_info=True
                    )
                    # Continue la surveillance même en cas d'erreur

                # Attente avant le prochain scan
                if not stop_watch:
                    logger.info(
                        f"\n⏳ Attente de {args.watch_interval}s avant le prochain scan...\n"
                    )
                    time.sleep(args.watch_interval)

            logger.info("\n✅ Surveillance arrêtée proprement")
            sys.exit(0)

        # Mode exécution unique (par défaut)
        else:
            result = pipeline.execute()

            # Compter les chunks en fonction de l'étape la plus avancée activée
            if "normalized_chunks" in result:
                chunk_count = len(result["normalized_chunks"])
            elif "enriched_chunks" in result:
                chunk_count = len(result["enriched_chunks"])
            elif "chunks" in result:
                chunk_count = len(result["chunks"])
            else:
                chunk_count = 0

            # Affichage du résultat
            print("\n✅ Pipeline exécuté avec succès!")
            print(f"Documents traités: {len(result.get('extracted_documents', []))}")
            print(f"Chunks créés: {chunk_count}")

            if result.get("storage_result"):
                storage = result["storage_result"]
                print(f"Chunks stockés: {storage.get('stored_count', 0)}")

    except Exception as e:
        logger.error(f"Erreur d'exécution: {e}", exc_info=True)
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
