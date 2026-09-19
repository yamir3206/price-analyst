"""Stable domain enumerations shared by the API and application services."""

from enum import StrEnum


class Marketplace(StrEnum):
    """Supported or planned source identifiers."""

    TOROB = "torob"
    BASALAM = "basalam"
    DIGIKALA = "digikala"
    DIVAR = "divar"
    INSTAGRAM = "instagram"
    OTHER = "other"


class Currency(StrEnum):
    """Currency codes used by collected offers.

    IRR and IRT are intentionally distinct. The system must not silently convert
    rial to toman because marketplace conventions are not always explicit.
    """

    IRR = "IRR"
    IRT = "IRT"
    UNKNOWN = "UNKNOWN"


class OfferCondition(StrEnum):
    NEW = "new"
    USED = "used"
    REFURBISHED = "refurbished"
    UNKNOWN = "unknown"


class Availability(StrEnum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"


class SourceState(StrEnum):
    READY = "ready"
    NOT_CONFIGURED = "not_configured"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    STALE = "stale"


class CollectionStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    NO_SOURCES_CONFIGURED = "no_sources_configured"
    FAILED = "failed"


class AIAnalysisStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    DISABLED = "disabled"
    CACHED = "cached"
    COMPLETED = "completed"
    INVALID_RESPONSE = "invalid_response"
    FAILED = "failed"
