import secrets
import hashlib
import time


_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_ulid() -> str:
    value = (int(time.time() * 1000) << 80) | secrets.randbits(80)
    encoded = ["0"] * 26
    for position in range(25, -1, -1):
        encoded[position] = _CROCKFORD[value & 31]
        value >>= 5
    return "".join(encoded)


def stable_ulid(value: str) -> str:
    number = int.from_bytes(hashlib.sha256(value.encode("utf-8")).digest()[:16], "big")
    encoded = ["0"] * 26
    for position in range(25, -1, -1):
        encoded[position] = _CROCKFORD[number & 31]
        number >>= 5
    return "".join(encoded)