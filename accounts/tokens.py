from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    # Separate salt so password-reset tokens can't be used here (and vice versa)
    key_salt = "accounts.tokens.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        # Includes is_verified, so the token dies the moment it's used
        return f"{user.pk}{user.email}{user.is_verified}{timestamp}"


email_verification_token = EmailVerificationTokenGenerator()