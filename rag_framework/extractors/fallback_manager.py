"""Gestionnaire de fallback pour l'extraction de texte."""

import time
from pathlib import Path
from typing import Any, ClassVar, Optional

from rag_framework.extractors.base import BaseExtractor, ExtractionResult
from rag_framework.extractors.docling_extractor import DoclingExtractor
from rag_framework.extractors.docx_extractor import DocxExtractor
from rag_framework.extractors.html_extractor import HTMLExtractor
from rag_framework.extractors.image_extractor import ImageExtractor
from rag_framework.extractors.marker_extractor import MarkerExtractor
from rag_framework.extractors.ocr_extractor import OCRExtractor
from rag_framework.extractors.pandas_extractor import PandasExtractor
from rag_framework.extractors.pdfplumber_extractor import PdfPlumberExtractor
from rag_framework.extractors.pptx_extractor import PptxExtractor
from rag_framework.extractors.pymupdf_extractor import PyMuPDFExtractor
from rag_framework.extractors.pypdf2_extractor import PyPDF2Extractor
from rag_framework.extractors.text_extractor import TextExtractor
from rag_framework.extractors.vlm_extractor import VLMExtractor
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class FallbackManager:
    """Gestionnaire de la chaîne de fallback pour l'extraction de texte.

    Ce gestionnaire essaie plusieurs extracteurs dans l'ordre jusqu'à
    ce qu'un réussisse. Si tous échouent, lève une exception.

    Supporte des profils prédéfinis pour différents cas d'usage :
    - speed : Privilégie la rapidité
    - memory : Minimise la RAM
    - compromise : Équilibre qualité/performance
    - quality : Maximise la qualité
    - custom : Configuration manuelle

    Architecture:
    -------------
    1. PyPDF2 (rapide, léger)
    2. Docling (OCR, layout analysis)
    3. Marker (ML-based, haute qualité)
    4. VLM (Vision AI, dernier recours)

    Parameters
    ----------
    config : dict[str, Any]
        Configuration du système de fallback.

    Attributes:
    ----------
    extractors : list[BaseExtractor]
        Liste des extracteurs initialisés.
    config : dict[str, Any]
        Configuration du fallback.
    profile : str
        Profil de fallback actif.
    """

    # Mapping nom → classe d'extracteur
    EXTRACTOR_CLASSES: ClassVar[dict[str, type[BaseExtractor]]] = {
        # Extracteurs rapides et gratuits (2025)
        "text": TextExtractor,  # Texte simple (.txt, .md, .xml, .svg, etc.)
        "pandas": PandasExtractor,  # Données tabulaires (.csv, .xlsx, .xls, .ods)
        "html": HTMLExtractor,  # HTML/XML avec BeautifulSoup
        "docx": DocxExtractor,  # Word (.docx, .docm) avec python-docx
        "pptx": PptxExtractor,  # PowerPoint (.pptx, .pptm) avec python-pptx
        # Extracteurs PDF (ordre: rapide → avancé)
        "pymupdf": PyMuPDFExtractor,  # PDF rapide (fitz)
        "pdfplumber": PdfPlumberExtractor,  # PDF + tableaux avancés
        "pypdf2": PyPDF2Extractor,  # PDF simple (fallback)
        # Extracteurs avancés/lourds
        "docling": DoclingExtractor,  # Universel (PDF/Office/OCR/layout)
        "marker": MarkerExtractor,  # PDF ML haute qualité
        "ocr": OCRExtractor,  # OCR Tesseract (images + PDF scannés)
        # Extracteurs VLM (nécessitent API)
        "image": ImageExtractor,  # Images avec VLM
        "vlm": VLMExtractor,  # VLM pour documents (dernier recours)
    }

    # Profils prédéfinis (meilleures pratiques 2025)
    PROFILES: ClassVar[dict[str, list[dict[str, Any]]]] = {
        # =====================================================================
        # Profil SPEED : Vitesse maximale, outils les plus rapides
        # =====================================================================
        # Ordre: text → pandas → html → pymupdf → pypdf2
        # Temps moyen: < 1 seconde par document
        # RAM: < 100 MB
        "speed": [
            {
                "name": "text",  # Texte simple (instantané)
                "enabled": True,
                "config": {"min_text_length": 10},
            },
            {
                "name": "pandas",  # CSV/Excel (très rapide)
                "enabled": True,
                "config": {"output_format": "markdown", "include_stats": False},
            },
            {
                "name": "html",  # HTML/XML (rapide avec lxml)
                "enabled": True,
                "config": {"parser": "lxml", "preserve_structure": False},
            },
            {
                "name": "pymupdf",  # PDF rapide (10-100x plus rapide que pypdf)
                "enabled": True,
                "config": {"preserve_layout": False, "min_text_length": 50},
            },
            {
                "name": "pypdf2",  # PDF fallback simple
                "enabled": True,
                "config": {"min_text_length": 50},
            },
        ],
        # =====================================================================
        # Profil MEMORY : Consommation mémoire minimale
        # =====================================================================
        # Ordre: text → pandas → html → docx → pptx → pymupdf → pypdf2 → docling
        # Pas de ML (marker), pas de VLM
        # RAM: < 200 MB
        "memory": [
            {
                "name": "text",
                "enabled": True,
                "config": {"min_text_length": 10},
            },
            {
                "name": "pandas",
                "enabled": True,
                "config": {
                    "output_format": "csv",
                    "include_stats": False,
                    "max_rows_display": 1000,
                },
            },
            {
                "name": "html",
                "enabled": True,
                "config": {"parser": "html.parser", "preserve_structure": False},
            },
            {
                "name": "docx",  # Word natif (léger)
                "enabled": True,
                "config": {
                    "extract_tables": False,
                    "extract_headers_footers": False,
                    "preserve_formatting": False,
                },
            },
            {
                "name": "pptx",  # PowerPoint natif (léger)
                "enabled": True,
                "config": {
                    "extract_notes": False,
                    "extract_tables": False,
                    "include_slide_numbers": False,
                },
            },
            {
                "name": "pymupdf",  # PDF léger
                "enabled": True,
                "config": {
                    "preserve_layout": False,
                    "extract_images": False,
                    "extract_metadata": False,
                },
            },
            {
                "name": "pypdf2",  # PDF fallback
                "enabled": True,
                "config": {"extract_metadata": False},
            },
            {
                "name": "docling",  # Universel en dernier recours
                "enabled": True,
                "config": {},  # Docling 1.x gère automatiquement
            },
        ],
        # =====================================================================
        # Profil COMPROMISE : Équilibre qualité/performance (RECOMMANDÉ)
        # =====================================================================
        # Ordre: text → pandas → html → docx → pptx → pdfplumber → pymupdf →
        #        pypdf2 → docling → ocr
        # Temps moyen: 2-5 secondes par document
        # RAM: < 500 MB
        "compromise": [
            {
                "name": "text",
                "enabled": True,
                "config": {"min_text_length": 10},
            },
            {
                "name": "pandas",
                "enabled": True,
                "config": {
                    "output_format": "markdown",
                    "include_stats": True,
                    "max_rows_display": 5000,
                },
            },
            {
                "name": "html",
                "enabled": True,
                "config": {
                    "parser": "lxml",
                    "preserve_structure": True,
                    "extract_metadata": True,
                },
            },
            {
                "name": "docx",  # Word natif (meilleur que docling pour .docx)
                "enabled": True,
                "config": {
                    "extract_tables": True,
                    "extract_headers_footers": True,
                    "preserve_formatting": False,
                },
            },
            {
                "name": "pptx",  # PowerPoint natif
                "enabled": True,
                "config": {
                    "extract_notes": True,
                    "extract_tables": True,
                    "include_slide_numbers": True,
                },
            },
            {
                "name": "pdfplumber",  # PDF avec tableaux (meilleur en 2025)
                "enabled": True,
                "config": {
                    "extract_tables": True,
                    "table_format": "markdown",
                    "preserve_layout": True,
                },
            },
            {
                "name": "pymupdf",  # PDF rapide fallback
                "enabled": True,
                "config": {"preserve_layout": True, "extract_metadata": True},
            },
            {
                "name": "pypdf2",  # PDF simple fallback
                "enabled": True,
                "config": {"extract_metadata": True},
            },
            {
                "name": "docling",  # Universel (OCR + layout)
                "enabled": True,
                "config": {},  # Docling 1.x auto
            },
            {
                "name": "ocr",  # OCR pour scans
                "enabled": True,
                "config": {
                    "lang": "fra+eng",
                    "psm": 3,
                    "preprocess": True,
                    "min_confidence": 0.5,
                },
            },
        ],
        # =====================================================================
        # Profil QUALITY : Qualité maximale (ML + VLM disponibles)
        # =====================================================================
        # Ordre: text → pandas → html → docx → pptx → pdfplumber → pymupdf →
        #        marker → docling → ocr → image → vlm
        # Temps moyen: 10-30 secondes par document
        # RAM: 500 MB - 2 GB
        "quality": [
            {
                "name": "text",
                "enabled": True,
                "config": {"min_text_length": 10},
            },
            {
                "name": "pandas",
                "enabled": True,
                "config": {
                    "output_format": "markdown",
                    "include_stats": True,
                },
            },
            {
                "name": "html",
                "enabled": True,
                "config": {
                    "parser": "lxml",
                    "preserve_structure": True,
                    "extract_links": True,
                    "extract_metadata": True,
                },
            },
            {
                "name": "docx",
                "enabled": True,
                "config": {
                    "extract_tables": True,
                    "extract_headers_footers": True,
                    "preserve_formatting": True,
                },
            },
            {
                "name": "pptx",
                "enabled": True,
                "config": {
                    "extract_notes": True,
                    "extract_tables": True,
                    "include_slide_numbers": True,
                },
            },
            {
                "name": "pdfplumber",  # PDF tableaux haute qualité
                "enabled": True,
                "config": {
                    "extract_tables": True,
                    "table_format": "markdown",
                    "preserve_layout": True,
                },
            },
            {
                "name": "pymupdf",  # PDF rapide fallback
                "enabled": True,
                "config": {"preserve_layout": True, "extract_metadata": True},
            },
            {
                "name": "marker",  # ML haute qualité pour PDF complexes
                "enabled": True,
                "config": {"use_gpu": False, "min_confidence": 0.6},
            },
            {
                "name": "docling",  # Universel avec OCR
                "enabled": True,
                "config": {},  # Docling 1.x auto
            },
            {
                "name": "ocr",  # OCR Tesseract pour scans
                "enabled": True,
                "config": {
                    "lang": "fra+eng",
                    "psm": 3,
                    "preprocess": True,
                    "min_confidence": 0.4,
                },
            },
            {
                "name": "image",  # VLM pour images
                "enabled": True,
                "config": {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "min_confidence": 0.4,
                },
            },
            {
                "name": "vlm",  # VLM dernier recours pour documents
                "enabled": True,
                "config": {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "max_pages": 10,
                    "min_confidence": 0.4,
                },
            },
        ],
    }

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise le gestionnaire de fallback.

        Parameters
        ----------
        config : dict[str, Any]
            Configuration du fallback depuis 02_preprocessing.yaml.
        """
        self.config = config
        self.extractors: list[BaseExtractor] = []
        self.profile = "custom"  # Défaut

        # Initialisation des extracteurs depuis la config
        self._initialize_extractors()

        logger.info(
            f"FallbackManager initialisé avec profil '{self.profile}' "
            f"et {len(self.extractors)} extracteurs"
        )

    def _initialize_extractors(self) -> None:
        """Initialise les extracteurs depuis la configuration ou le profil."""
        fallback_config = self.config.get("fallback", {})

        if not fallback_config.get("enabled", False):
            logger.warning("Système de fallback désactivé")
            return

        # Récupération du mode VLM (standard vs VLM)
        use_vlm = fallback_config.get("use_vlm", False)
        vlm_extractors = {"image", "vlm"}  # Extracteurs nécessitant VLM

        if not use_vlm:
            logger.info(
                "Mode STANDARD activé (use_vlm=false). "
                "Les extracteurs VLM (image, vlm) seront ignorés."
            )
        else:
            logger.info(
                "Mode VLM activé (use_vlm=true). "
                "Les extracteurs VLM seront disponibles en fallback."
            )

        # Récupération du profil (speed/memory/compromise/quality/custom)
        profile_name = fallback_config.get("profile", "custom")
        self.profile = profile_name

        # Si profil prédéfini, utiliser la config du profil
        if profile_name in self.PROFILES:
            logger.info(f"Utilisation du profil prédéfini: '{profile_name}'")
            extractors_config = self.PROFILES[profile_name]
        else:
            # Profil "custom" ou inconnu : utiliser config manuelle
            if profile_name != "custom":
                logger.warning(
                    f"Profil inconnu: '{profile_name}'. Utilisation de 'custom'"
                )
            extractors_config = fallback_config.get("extractors", [])

        for extractor_cfg in extractors_config:
            name = extractor_cfg.get("name")
            enabled = extractor_cfg.get("enabled", True)
            config = extractor_cfg.get("config", {})

            # Validation du nom
            if not name or not isinstance(name, str):
                logger.warning("Configuration extracteur invalide: 'name' manquant")
                continue

            if not enabled:
                logger.debug(f"Extracteur '{name}' désactivé")
                continue

            # Filtrage des extracteurs VLM si use_vlm=false
            if not use_vlm and name in vlm_extractors:
                logger.debug(
                    f"Extracteur '{name}' ignoré (mode standard, use_vlm=false)"
                )
                continue

            # Récupération de la classe d'extracteur
            extractor_class = self.EXTRACTOR_CLASSES.get(name)

            if not extractor_class:
                logger.warning(f"Extracteur inconnu: '{name}'. Ignoré.")
                continue

            try:
                # Instanciation de l'extracteur
                extractor = extractor_class(config)
                self.extractors.append(extractor)
                logger.debug(f"Extracteur '{name}' initialisé")

            except Exception as e:
                logger.error(f"Erreur initialisation extracteur '{name}': {e}")

        if not self.extractors:
            logger.warning("Aucun extracteur disponible !")

    def extract_with_fallback(
        self, file_path: Path
    ) -> tuple[ExtractionResult, Optional[str]]:
        """Extrait le texte avec fallback automatique.

        Essaie chaque extracteur dans l'ordre jusqu'à ce qu'un réussisse.
        Retourne le premier résultat valide ou lève une exception.

        Parameters
        ----------
        file_path : Path
            Chemin vers le fichier à extraire.

        Returns:
        -------
        tuple[ExtractionResult, Optional[str]]
            (Résultat d'extraction, Nom de l'extracteur qui a réussi).

        Raises:
        ------
        Exception
            Si tous les extracteurs échouent.

        Examples:
        --------
        >>> manager = FallbackManager(config)
        >>> result, extractor_name = manager.extract_with_fallback(Path("doc.pdf"))
        >>> print(f"Extrait {len(result.text)} chars avec {extractor_name}")
        """
        if not self.extractors:
            raise RuntimeError("Aucun extracteur disponible dans le FallbackManager")

        logger.info(f"Extraction avec fallback de: {file_path.name}")

        # Liste pour tracker les échecs
        failures: list[tuple[str, str]] = []

        # Essayer chaque extracteur dans l'ordre
        for extractor in self.extractors:
            # Vérifier si l'extracteur peut traiter ce type de fichier
            if not extractor.can_extract(file_path):
                logger.debug(
                    f"Extracteur '{extractor.name}' ne supporte pas {file_path.suffix}"
                )
                continue

            logger.info(f"Tentative extraction avec '{extractor.name}'...")

            try:
                # Mesure du temps d'extraction
                start_time = time.time()

                # Extraction
                result = extractor.extract(file_path)

                extraction_time = time.time() - start_time

                # Ajout du temps d'extraction aux métadonnées
                result.metadata["extraction_time_seconds"] = round(extraction_time, 2)

                # Validation du résultat
                if extractor.validate_result(result):
                    logger.info(
                        f"✓ Extraction réussie avec '{extractor.name}' "
                        f"({len(result.text)} chars, "
                        f"confidence={result.confidence_score:.2f}, "
                        f"time={extraction_time:.2f}s)"
                    )
                    return result, extractor.name

                else:
                    # Résultat invalide, passer au suivant
                    reason = (
                        result.error
                        if result.error
                        else "Résultat invalide (validation échouée)"
                    )
                    logger.warning(
                        f"✗ Extraction avec '{extractor.name}' invalide: {reason}"
                    )
                    failures.append((extractor.name, reason))

            except Exception as e:
                # Erreur durant l'extraction, passer au suivant
                error_msg = f"Exception: {e}"
                logger.warning(f"✗ Extraction avec '{extractor.name}' échouée: {e}")
                failures.append((extractor.name, error_msg))

        # Si on arrive ici, tous les extracteurs ont échoué
        failure_summary = "\n".join(
            [f"  - {name}: {reason}" for name, reason in failures]
        )

        error_message = (
            f"Échec d'extraction pour {file_path.name}. "
            f"Tous les extracteurs ont échoué:\n{failure_summary}"
        )

        logger.error(error_message)
        raise RuntimeError(error_message)

    def get_available_extractors(self) -> list[str]:
        """Retourne la liste des extracteurs disponibles.

        Returns:
        -------
        list[str]
            Noms des extracteurs initialisés.
        """
        return [ext.name for ext in self.extractors]
