import secrets
import string 

def generate_temporary_password():

    uppercase = secrets.choice(string.ascii_uppercase)
    lowercase = secrets.choice(string.ascii_lowercase)
    digit = secrets.choice(string.digits)
    symbol = secrets.choice("!@#$%^&*")

    remaining = [
        secrets.choice(
            string.ascii_letters +
            string.digits +
            "!@#$%^&*"
        )
        for _ in range(4)
    ]

    password_characters = [
        uppercase,
        lowercase,
        digit,
        symbol,
        *remaining,
    ]

    secrets.SystemRandom().shuffle(password_characters)

    return "".join(password_characters) 