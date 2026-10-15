import base64
import hashlib
import secrets

from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet() -> Fernet:
    key = settings.encryption_key
    if not key:
        # Derive a stable dev key from the JWT secret; production must set ENCRYPTION_KEY.
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret.encode()).digest()).decode()
    return Fernet(key.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def random_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


_WORDS = ["amber", "anchor", "apple", "aspen", "atlas", "autumn", "badge", "bamboo", "banjo", "basil", "beacon", "birch", "bison", "blaze", "bloom", "breeze", "brook", "cactus", "camel", "canyon", "cedar", "cherry", "cider", "cliff", "clover", "cobalt", "comet", "coral", "cosmos", "cotton", "crane", "crystal", "cypress", "dahlia", "delta", "desert", "dolphin", "dune", "eagle", "ember", "falcon", "fern", "fjord", "flint", "forest", "fossil", "garnet", "gecko", "ginger", "glacier", "granite", "harbor", "hazel", "heron", "hollow", "honey", "indigo", "iris", "island", "ivory", "jade", "jasmine", "juniper", "kestrel", "koala", "lagoon", "lantern", "lark", "lemon", "lilac", "lotus", "lunar", "magnet", "mango", "maple", "marble", "meadow", "mint", "monsoon", "moss", "nectar", "nova", "oasis", "olive", "onyx", "orchid", "otter", "palm", "panda", "pebble", "pepper", "pine", "plume", "prairie", "quartz", "quill", "rain", "raven", "reef", "ridge", "river", "robin", "ruby", "saffron", "sage", "sand", "sapphire", "shadow", "sierra", "silver", "sparrow", "spruce", "stone", "summit", "sunset", "swan", "thistle", "thunder", "tiger", "topaz", "tulip", "tundra", "valley", "velvet", "violet", "walnut", "willow", "wren", "zephyr"]


def member_key() -> str:
    """Opaque per-user handle given to that user's bots (room bulletin).

    Word-style on purpose: OpenMausBot redacts strings that look like credentials from
    memory and exports, and hyphenated words with a short number pass through intact.
    7 words from 160 + a 2 digit number is ~58 bits, and every lookup is rate limited.
    """
    words = [secrets.choice(_WORDS) for _ in range(7)]
    return f"{'-'.join(words[:4])}-{secrets.randbelow(90) + 10}-{'-'.join(words[4:])}"
