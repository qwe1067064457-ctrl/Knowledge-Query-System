import logging
import os

logger = logging.getLogger(__name__)

def read_file(file_path: str) -> str:
    logger.info(f"Reading file: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content

def write_file(file_path: str, content: str) -> None:
    logger.info(f"Writing to file: {file_path}")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def delete_file(file_path: str) -> None:
    logger.info(f"Deleting file: {file_path}")
    if os.path.exists(file_path):
        os.remove(file_path)
    else:
        logger.warning(f"File not found for deletion: {file_path}")
