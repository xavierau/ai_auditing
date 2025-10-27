"""
Password policy validation for user authentication security.

Enforces password complexity requirements following security best practices.
Sprint 6 Phase 2: Security Testing
"""

import re
from typing import Tuple


class PasswordPolicy:
    """
    Password complexity policy validator.

    Requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - Not a common weak password
    """

    MIN_LENGTH = 12

    # Common weak passwords to reject
    COMMON_PASSWORDS = {
        "password",
        "password123",
        "12345678",
        "qwerty",
        "abc123",
        "letmein",
        "welcome",
        "admin123",
        "password1",
        "iloveyou",
    }

    def validate(self, password: str) -> bool:
        """
        Validate password against policy.

        Args:
            password: Password to validate

        Returns:
            True if password meets all requirements, False otherwise
        """
        is_valid, _ = self.validate_with_reason(password)
        return is_valid

    def validate_with_reason(self, password: str) -> Tuple[bool, str]:
        """
        Validate password and return reason for failure.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, reason)
            - (True, "") if valid
            - (False, "reason") if invalid
        """
        # Check minimum length
        if len(password) < self.MIN_LENGTH:
            return False, f"Password must be at least {self.MIN_LENGTH} characters"

        # Check for common passwords
        if password.lower() in self.COMMON_PASSWORDS:
            return False, "Password is too common"

        # Check for uppercase letter
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"

        # Check for lowercase letter
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"

        # Check for digit
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"

        # Check for special character
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character"

        return True, ""
