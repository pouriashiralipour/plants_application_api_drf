"""
OTP (One-Time Password) service using Django cache backend.

This module provides a lightweight OTP service built on top of Django’s
caching framework. It handles **OTP generation, delivery, storage, and
verification** with built-in protection against brute-force attacks.

Features:
    - Generate secure numeric OTP codes.
    - Store OTP codes in cache with expiration (default: 120 seconds).
    - Prevent multiple OTPs from being sent before expiry.
    - Enforce maximum verification attempts (default: 5).
    - Verify OTP codes against their stored purpose.
    - Delete OTP codes after successful verification or when attempts exceed.

Constants:
    OTP_TTL_SECONDS (int): Time-to-live for an OTP in seconds (default: 120).
    MAX_OTP_ATTEMPTS (int): Maximum allowed verification attempts (default: 5).

Example:
    >>> OTPService.send_otp(target="+989123456789", purpose="login", channel="sms")
    True

    >>> OTPService.verify_otp(target="+989123456789", code="123456", purpose="login")
    {'code': '123456', 'purpose': 'login', 'attempts': 0}
"""

import secrets
import string
from typing import Optional

from django.core.cache import cache

OTP_TTL_SECONDS = 120
MAX_OTP_ATTEMPTS = 5


class OTPService:
    """
    Service for managing OTP generation, delivery, and verification.

    OTPs are stored in Django’s cache backend under the key pattern
    ``otp:{target}``. Each entry contains:
        - code (str): The OTP code.
        - purpose (str): The purpose of the OTP (e.g., "login", "password_reset").
        - attempts (int): The number of failed verification attempts.

    Methods:
        _generate_code(length=6):
            Generate a secure numeric OTP code.

        send_otp(target, purpose, channel):
            Generate and store an OTP for a given target (e.g., phone/email).

        verify_otp(target, code, purpose):
            Validate an OTP against the stored value and enforce brute-force limits.
    """

    @staticmethod
    def _generate_code(length: int = 6) -> str:
        """
        Generate a secure numeric OTP code.

        Uses Python's `secrets` module for cryptographically secure random values.

        Args:
            length (int, optional): The number of digits in the OTP code.
                Defaults to 6.

        Returns:
            str: A randomly generated numeric OTP code.

        Example:
            >>> OTPService._generate_code()
            '493027'
        """

        return "".join(secrets.choice(string.digits) for i in range(length))

    @staticmethod
    def send_otp(target: str, purpose: str, channel: str) -> bool:
        """
        Send and cache an OTP for a specific target and purpose.

        An OTP will not be resent if one already exists in cache
        (until it expires).

        Args:
            target (str): The OTP recipient identifier (e.g., phone number or email).
            purpose (str): The intended purpose of the OTP (e.g., "login").
            channel (str): Delivery method (e.g., "sms", "email").
                *Note: For now, OTP is printed to console for debugging.*

        Returns:
            bool: True if OTP was generated and stored successfully,
            False if an active OTP already exists.

        Example:
            >>> OTPService.send_otp("+989123456789", "login", "sms")
            True
        """

        if cache.get(f"otp:{target}"):
            return False

        code = OTPService._generate_code()
        otp_data = {
            "code": code,
            "purpose": purpose,
            "attempts": 0,
        }

        cache.set(f"otp:{target}", otp_data, timeout=OTP_TTL_SECONDS)

        print(f"OTP for {target} ({purpose}): {code}")

        return True

    @staticmethod
    def verify_otp(target: str, code: str, purpose: str) -> Optional[dict]:
        """
        Verify an OTP code for a given target and purpose.

        Rules:
            - If no OTP exists in cache, return None.
            - If the stored purpose does not match, return None.
            - If max attempts are exceeded, delete OTP and return None.
            - If code matches, delete OTP and return the OTP data.
            - Otherwise, increment attempts and return None.

        Args:
            target (str): The OTP recipient identifier.
            code (str): The OTP code provided by the user.
            purpose (str): The intended purpose (must match the stored one).

        Returns:
            dict | None: OTP data on success (with keys "code", "purpose", "attempts"),
            otherwise None.

        Example:
            >>> OTPService.verify_otp("+989123456789", "123456", "login")
            {'code': '123456', 'purpose': 'login', 'attempts': 0}
        """

        key = f"otp:{target}"
        otp_data = cache.get(key)

        if not otp_data:
            return None

        if otp_data["purpose"] != purpose:
            return None

        if otp_data["attempts"] >= MAX_OTP_ATTEMPTS:
            cache.delete(key)
            return None

        if otp_data["code"] == code:
            cache.delete(key)
            return otp_data
        else:
            otp_data["attempts"] += 1

        cache.set(key, otp_data, timeout=cache.ttl(key))
        return None
