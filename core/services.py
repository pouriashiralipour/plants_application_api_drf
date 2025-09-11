import secrets
import string
from typing import Optional

from django.core.cache import cache

OTP_TTL_SECONDS = 120
MAX_OTP_ATTEMPTS = 5


class OTPService:
    @staticmethod
    def _generate_code(length: int = 6) -> str:
        return "".join(secrets.choice(string.digits) for i in range(length))

    @staticmethod
    def send_otp(target: str, purpose: str, channel: str) -> bool:
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
