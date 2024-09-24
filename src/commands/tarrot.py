import os
import random
from pathlib import Path


class ImageNotFoundError(Exception):
    pass


def extract_tarot_file() -> Path:
    current_dir = os.path.dirname(__file__)
    TAROTS_BANK = os.path.join(current_dir, 'persist', 'tarots')
    if not os.path.exists(TAROTS_BANK):
        raise NotADirectoryError(TAROTS_BANK)
    else:
        extracted_file = random.choice(os.listdir(TAROTS_BANK))
        extracted_file = os.path.join(TAROTS_BANK, extracted_file)
        if not any(os.scandir(TAROTS_BANK)) or not extracted_file.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
            raise ImageNotFoundError
        return Path(extracted_file)


def main() -> None:
    print(extract_tarot_file())


if __name__ == '__main__':
    main()
