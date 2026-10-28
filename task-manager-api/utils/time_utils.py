from datetime import datetime, timezone


def utc_now():
    """UTC naive, compatível com as colunas DateTime existentes."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
