# -*- coding: utf-8 -*-
"""
Shadowsocks cipher (encrypt method) metadata and helpers.

Single source of truth for:
  * which methods are Shadowsocks-2022 (SIP022 AEAD-2022) ciphers and their key sizes
  * generating a conforming password for a method
  * validating that a password conforms to a method

For SS-2022 ciphers the password MUST be a Base64-encoded key (PSK) of exactly the
cipher's key size; arbitrary passwords are rejected by the server. shadowsocks-libev
does not implement the SS-2022 ciphers -- they require the `rust` server edition
(shadowsocks-rust), see https://github.com/alexzhangs/shadowsocks-rust .
"""

import os
import base64

# SS-2022 (SIP022) methods -> required key size in bytes.
AEAD_2022_METHODS = {
    '2022-blake3-aes-128-gcm': 16,
    '2022-blake3-aes-256-gcm': 32,
    '2022-blake3-chacha20-poly1305': 32,
}

# Length for legacy (non-2022) random passwords.
DEFAULT_PASSWORD_LENGTH = 16


def is_2022(method):
    """Return True if `method` is a Shadowsocks-2022 (SIP022) cipher."""
    return method in AEAD_2022_METHODS


def key_size(method):
    """Return the required key size in bytes for a SS-2022 `method`, else None."""
    return AEAD_2022_METHODS.get(method)


def generate_password(method=None):
    """
    Generate a password suitable for `method`.

    For SS-2022 ciphers, returns a Base64-encoded random key (PSK) of exactly the
    cipher's key size -- equivalent to `ssservice genkey -m <method>`. For any other
    method (or None), returns a random alphanumeric string.
    """
    size = key_size(method)
    if size is not None:
        return base64.b64encode(os.urandom(size)).decode('ascii')

    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits,
                                  k=DEFAULT_PASSWORD_LENGTH))


def is_valid_password(method, password):
    """
    Return True if `password` is valid for `method`.

    For SS-2022 ciphers, the password must be a Base64 string that decodes to exactly
    the cipher's key size. For any other method, any non-empty password is accepted.
    """
    size = key_size(method)
    if size is None:
        return bool(password)
    try:
        raw = base64.b64decode(password, validate=True)
    except Exception:
        return False
    return len(raw) == size
