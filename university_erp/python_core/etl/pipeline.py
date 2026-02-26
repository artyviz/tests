"""
University ERP — ETL Pipeline Orchestrator

Wires Extractor → Transformer → Validator → Loader into a
single executable pipeline.  Components are resolved from
settings.yaml class paths at runtime for hot-swap support.
"""

from __future__ import annotations

import importlib
from typing import Any, Dict, List, Optional, Type

from python_core.base import (
    BaseExtractor,
    BaseLoader,
    BaseTransformer,
    BaseValidator,
    ValidationResult,
)
from python_core.utils.exceptions import ETLPipelineError
from python_core.utils.logger import ERPLogger

_log = ERPLogger.get_logger("etl.pipeline")


class ETLPipeline:
    """
    Orchestrates the full ETL+V flow:

        1. **Extract** — pull raw records from a source
        2. **Transform** — normalise / clean
        3. **Validate** — schema + business-rule checks
        4. **Load** — persist valid records

    Components can be injected directly or resolved dynamically
    from dotted class paths (configured in settings.yaml).
    """

    def __init__(
        self,
        *,
        extractor: Optional[BaseExtractor] = None,
        transformer: Optional[BaseTransformer] = None,
        validator: Optional[BaseValidator] = None,
        loader: Optional[BaseLoader] = None,
        extractor_class: Optional[str] = None,
        transformer_class: Optional[str] = None,
        validator_class: Optional[str] = None,
        loader_class: Optional[str] = None,
    ) -> None:
        self._extractor = extractor or self._resolve(extractor_class, BaseExtractor)
        self._transformer = transformer or self._resolve(transformer_class, BaseTransformer)
        self._validator = validator or self._resolve(validator_class, BaseValidator)
        self._loader = loader or self._resolve(loader_class, BaseLoader)

    # ── Public API ───────────────────────────────────────────
    def run(
        self,
        source: Any,
        destination: Any,
        *,
        skip_invalid: bool = True,
    ) -> "PipelineResult":
        """
        Execute the full ETL+V pipeline.

        Args:
            source:        passed to the Extractor
            destination:   passed to the Loader
            skip_invalid:  if True, load only valid records;
                           if False, raise on first invalid record

        Returns:
            PipelineResult with metrics and any validation errors.
        """
        _log.info("═══ ETL Pipeline START ═══")

        # 1 — EXTRACT
        _log.info("▸ Stage: EXTRACT")
        raw_data = self._extractor.extract(source)
        _log.info("  Extracted %d records", len(raw_data))

        # 2 — TRANSFORM
        _log.info("▸ Stage: TRANSFORM")
        transformed = self._transformer.transform(raw_data)
        _log.info("  Transformed %d records", len(transformed))

        # 3 — VALIDATE
        _log.info("▸ Stage: VALIDATE")
        validation = self._validator.validate(transformed)
        _log.info(
            "  Validation: %d valid, %d invalid",
            len(validation.valid_records),
            len(validation.invalid_records),
        )

        if not skip_invalid and not validation.is_valid:
            raise ETLPipelineError(
                "Validator",
                f"{len(validation.invalid_records)} records failed validation",
            )

        records_to_load = validation.valid_records

        # 4 — LOAD
        _log.info("▸ Stage: LOAD")
        loaded_count = self._loader.load(records_to_load, destination)
        _log.info("  Loaded %d records", loaded_count)

        _log.info("═══ ETL Pipeline COMPLETE ═══")

        return PipelineResult(
            extracted=len(raw_data),
            transformed=len(transformed),
            valid=len(validation.valid_records),
            invalid=len(validation.invalid_records),
            loaded=loaded_count,
            validation_errors=validation.errors,
        )

    # ── Component swapping ───────────────────────────────────
    def set_extractor(self, extractor: BaseExtractor) -> None:
        self._extractor = extractor

    def set_transformer(self, transformer: BaseTransformer) -> None:
        self._transformer = transformer

    def set_validator(self, validator: BaseValidator) -> None:
        self._validator = validator

    def set_loader(self, loader: BaseLoader) -> None:
        self._loader = loader

    # ── Dynamic class resolution ─────────────────────────────
    @staticmethod
    def _resolve(class_path: Optional[str], base_type: type) -> Any:
        """
        Import and instantiate a class from a dotted path like
        'python_core.etl.extractor.CSVExtractor'.
        """
        if not class_path:
            raise ETLPipelineError(
                "Pipeline",
                f"No class path provided for {base_type.__name__}",
            )
        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            if not issubclass(cls, base_type):
                raise ETLPipelineError(
                    "Pipeline",
                    f"{class_path} is not a subclass of {base_type.__name__}",
                )
            return cls()
        except (ImportError, AttributeError) as exc:
            raise ETLPipelineError(
                "Pipeline", f"Cannot resolve class '{class_path}': {exc}"
            ) from exc


class PipelineResult:
    """Immutable summary of a pipeline run."""

    __slots__ = (
        "_extracted",
        "_transformed",
        "_valid",
        "_invalid",
        "_loaded",
        "_validation_errors",
    )

    def __init__(
        self,
        extracted: int,
        transformed: int,
        valid: int,
        invalid: int,
        loaded: int,
        validation_errors: List[Dict[str, Any]],
    ) -> None:
        self._extracted = extracted
        self._transformed = transformed
        self._valid = valid
        self._invalid = invalid
        self._loaded = loaded
        self._validation_errors = validation_errors

    @property
    def extracted(self) -> int:
        return self._extracted

    @property
    def transformed(self) -> int:
        return self._transformed

    @property
    def valid(self) -> int:
        return self._valid

    @property
    def invalid(self) -> int:
        return self._invalid

    @property
    def loaded(self) -> int:
        return self._loaded

    @property
    def validation_errors(self) -> List[Dict[str, Any]]:
        return list(self._validation_errors)

    @property
    def success_rate(self) -> float:
        total = self._valid + self._invalid
        return (self._valid / total * 100) if total > 0 else 0.0

    def __repr__(self) -> str:
        return (
            f"<PipelineResult extracted={self._extracted} "
            f"transformed={self._transformed} valid={self._valid} "
            f"invalid={self._invalid} loaded={self._loaded} "
            f"success_rate={self.success_rate:.1f}%>"
        )
