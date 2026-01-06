# common/id_generator.py

import random
import string


def generate_group_id(length: int = 6) -> str:
    """
    Генерирует случайный идентификатор группы из цифр и
    заглавных латинских букв, длиной length символов.
    Например: 'A9F3Z1'.

    length по умолчанию = 6.
    """
    alphabet = string.ascii_uppercase + string.digits  # A-Z и 0-9
    return "".join(random.choices(alphabet, k=length))
