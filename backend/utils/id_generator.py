import string
import secrets

def distress_token_id_generator(prefix="TK-2026-UK") -> str:
    random_chars = "".join(
        secrets.choice(string.ascii_uppercase + string.digits)
        for _ in range(6)
    )

    return f"{prefix}-{random_chars}"

def rescue_team_id_generator(prefix="UK-2026-RES") -> str:
    random_chars = "".join(
        secrets.choice(string.ascii_uppercase + string.digits)
        for _ in range(4)
    )

    return f"{prefix}-{random_chars}"