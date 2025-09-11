import secrets
import string


class OTPService:
    @staticmethod
    def _generate_code(length: int = 6) -> str:
        return "".join(secrets.choice(string.digits) for i in range(length))
