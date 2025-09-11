import secrets
import string

from django.core.cache import cache

OTP_TTL_SECONDS = 120


class OTPService:
    @staticmethod
    def _generate_code(length: int = 6) -> str:
        return "".join(secrets.choice(string.digits) for i in range(length))

    @staticmethod
    def send_otp(target: str, purpose: str, channel: str) -> bool:
        if cache.get(f"OTP:{target}"):
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
