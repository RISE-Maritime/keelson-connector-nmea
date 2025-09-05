from typing import Optional


def extract_rot_value(sentence: str) -> Optional[float]:
    """Return the rate-of-turn value from a ROT sentence.

    Tries to use ``pynmea2`` if available and falls back to a basic
    comma-split parse for environments without the library.
    """
    rot_value = None
    try:
        import pynmea2  # type: ignore

        data = pynmea2.parse(sentence)
        for attr in ("rate", "rate_of_turn", "rot"):
            if hasattr(data, attr):
                rot_value = getattr(data, attr)
                break
    except Exception:
        # Fallback: parse second field directly
        try:
            rot_value = sentence.split(",")[1]
        except Exception:
            rot_value = None

    if rot_value is None:
        return None

    try:
        return float(rot_value)
    except Exception:
        return None
