"""Kleine, allgemeine Hilfsfunktionen ohne eigene fachliche Heimat."""


def format_ms(ms: int) -> str:
    """Millisekunden in m:ss bzw. h:mm:ss umwandeln."""
    total_seconds = ms // 1000
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes}:{seconds:02}"
