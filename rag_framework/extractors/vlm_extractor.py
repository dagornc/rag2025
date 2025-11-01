"""Extracteur basé sur VLM (Vision Language Model) - dernier recours."""

from pathlib import Path
from typing import Any

from rag_framework.config import get_llm_client, load_config
from rag_framework.extractors.base import BaseExtractor, ExtractionResult
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class VLMExtractor(BaseExtractor):
    """Extracteur utilisant un Vision Language Model pour extraction visuelle.

    Cette méthode convertit le document en images et utilise un modèle vision
    (comme GPT-4 Vision, Claude 3, LLaVA, etc.) pour extraire le texte.

    Cas d'usage:
    - Dernier recours quand tous les autres extracteurs échouent
    - PDF scannés de mauvaise qualité
    - Documents avec mise en page très complexe
    - Documents manuscrits

    Avantages:
    - Fonctionne sur TOUS les types de documents
    - Comprend le contexte visuel (graphiques, tableaux, etc.)
    - Peut extraire même de documents manuscrits

    Limitations:
    - TRÈS lent (appels API pour chaque page)
    - Coûteux (coût par token du VLM)
    - Nécessite conversion PDF → images
    - Dépend de la disponibilité du service VLM

    Parameters
    ----------
    config : dict[str, Any]
        Configuration de l'extracteur.
        Clés supportées:
        - provider : str (ex: "openai", "anthropic")
        - model : str (ex: "gpt-4-vision-preview", "claude-3-opus")
        - temperature : float (défaut: 0.0)
        - max_tokens_per_page : int (défaut: 2000)
        - max_pages : int (défaut: None)
        - prompt : str (prompt personnalisé)
        - image_dpi : int (défaut: 200)
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise l'extracteur VLM.

        Parameters
        ----------
        config : dict[str, Any]
            Configuration de l'extracteur.
        """
        super().__init__(config)

        # Chargement de la config globale pour accès aux VLM providers
        self.global_config = load_config()

        # Initialisation du client VLM si configuré
        self.vlm_client = None
        if config.get("provider") and config.get("model"):
            try:
                self.vlm_client = get_llm_client(
                    provider_name=config["provider"],
                    model=config["model"],
                    temperature=config.get("temperature", 0.0),
                    global_config=self.global_config,
                )
                logger.info(
                    f"VLM Extractor initialisé: {config['provider']}/{config['model']}"
                )
            except Exception as e:
                logger.warning(f"Erreur initialisation VLM client: {e}")
                self.vlm_client = None

    def can_extract(self, file_path: Path) -> bool:
        """Vérifie si VLM peut traiter ce fichier.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier.

        Returns:
        -------
        bool
            True si VLM est configuré et le fichier est PDF ou image.
        """
        if not self.vlm_client:
            return False

        # VLM peut traiter PDF et images
        supported_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
        return file_path.suffix.lower() in supported_extensions

    def extract(self, file_path: Path) -> ExtractionResult:
        """Extrait le texte avec VLM.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier.

        Returns:
        -------
        ExtractionResult
            Résultat de l'extraction.
        """
        if not self.vlm_client:
            error_msg = "VLM client non initialisé"
            return ExtractionResult(
                text="",
                success=False,
                extractor_name=self.name,
                metadata={},
                error=error_msg,
                confidence_score=0.0,
            )

        try:
            # Conversion du document en images
            images = self._convert_to_images(file_path)

            if not images:
                return ExtractionResult(
                    text="",
                    success=False,
                    extractor_name=self.name,
                    metadata={},
                    error="Échec conversion en images",
                    confidence_score=0.0,
                )

            # Limitation du nombre de pages si configuré
            max_pages = self.config.get("max_pages", None)
            if max_pages:
                images = images[:max_pages]

            logger.info(f"VLM: Traitement de {len(images)} pages...")

            # Extraction du texte page par page
            extracted_pages = []
            for page_num, image_path in enumerate(images, 1):
                logger.debug(f"VLM: Extraction page {page_num}/{len(images)}")

                page_text = self._extract_from_image(image_path, page_num)
                if page_text:
                    extracted_pages.append(page_text)

            # Concaténation de toutes les pages
            full_text = "\n\n---\n\n".join(extracted_pages)

            # Métadonnées
            metadata = {
                "file_size": file_path.stat().st_size,
                "file_name": file_path.name,
                "num_pages_processed": len(images),
                "vlm_provider": self.config.get("provider"),
                "vlm_model": self.config.get("model"),
            }

            # Score de confiance moyen pour VLM (dépend de la qualité du modèle)
            confidence = 0.8 if full_text and len(full_text) > 100 else 0.4

            logger.info(
                f"VLM: Extrait {len(full_text)} caractères "
                f"depuis {len(images)} pages "
                f"(confidence={confidence:.2f})"
            )

            return ExtractionResult(
                text=full_text,
                success=True,
                extractor_name=self.name,
                metadata=metadata,
                confidence_score=confidence,
            )

        except Exception as e:
            error_msg = f"Erreur VLM extraction: {e}"
            logger.error(error_msg)
            return ExtractionResult(
                text="",
                success=False,
                extractor_name=self.name,
                metadata={},
                error=error_msg,
                confidence_score=0.0,
            )

    def _convert_to_images(self, file_path: Path) -> list[Path]:
        """Convertit un document en liste d'images.

        Parameters
        ----------
        file_path : Path
            Chemin vers le document (PDF ou image).

        Returns:
        -------
        list[Path]
            Liste des chemins vers les images générées.
        """
        try:
            # Si c'est déjà une image, retour direct
            if file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                return [file_path]

            # Conversion PDF → images
            from pdf2image import convert_from_path

            dpi = self.config.get("image_dpi", 200)

            logger.debug(f"Conversion PDF en images (DPI={dpi})...")
            images = convert_from_path(
                str(file_path),
                dpi=dpi,
                fmt="png",
            )

            # Sauvegarde temporaire des images
            import tempfile

            temp_dir = Path(tempfile.mkdtemp())
            image_paths = []

            for i, image in enumerate(images):
                image_path = temp_dir / f"page_{i+1}.png"
                image.save(str(image_path), "PNG")
                image_paths.append(image_path)

            logger.debug(f"Généré {len(image_paths)} images temporaires")
            return image_paths

        except ImportError:
            logger.error(
                "pdf2image non installé. Installez avec: pip install pdf2image"
            )
            return []
        except Exception as e:
            logger.error(f"Erreur conversion PDF → images: {e}")
            return []

    def _extract_from_image(self, image_path: Path, page_num: int) -> str:
        """Extrait le texte d'une image avec VLM.

        Parameters
        ----------
        image_path : Path
            Chemin vers l'image.
        page_num : int
            Numéro de la page.

        Returns:
        -------
        str
            Texte extrait de l'image.
        """
        try:
            import base64

            # Lecture et encodage de l'image en base64
            with open(image_path, "rb") as img_file:
                image_data = base64.b64encode(img_file.read()).decode("utf-8")

            # Récupération du prompt personnalisé ou utilisation du défaut
            prompt = self.config.get(
                "prompt",
                """Extract all text from this document page.
Preserve the structure and formatting as much as possible.
Include all visible text, tables, and captions.
Return only the extracted text without any commentary.""",
            )

            # Appel au VLM
            # Note: L'API varie selon le provider (OpenAI, Anthropic, etc.)
            # On utilise le format OpenAI compatible
            assert self.vlm_client is not None

            response = self.vlm_client.chat.completions.create(
                model=self.vlm_client._model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_data}"
                                },
                            },
                        ],
                    }
                ],
                temperature=self.vlm_client._temperature,
                max_tokens=self.config.get("max_tokens_per_page", 2000),
            )

            # Extraction du texte de la réponse
            if response.choices and response.choices[0].message.content:
                content: str = str(response.choices[0].message.content).strip()
                return content

            return ""

        except Exception as e:
            logger.error(f"Erreur extraction VLM page {page_num}: {e}")
            return ""
