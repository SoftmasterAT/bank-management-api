import logging
import sys
import os


# Verzeichnis für Log-Dateien
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def get_bank_logger():
    """
    Erstellt und konfiguriert den zentralen Logger für das Projekt.

    Returns:
        logger: Logger
    """
    logger = logging.getLogger("Softmaster_Bank")

    # Verhindert doppelte Logs, falls der Logger mehrfach aufgerufen wird
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Format: Zeit | Level | Modul | Nachricht
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%d-%m-%Y %H:%M:%S'
        )

        # 1. StreamHandler für die Konsole (für Docker & Azure Logs)
        console_handler = logging.StreamHandler(sys.stdout)
        # console_handler.setLevel(logging.WARNING) # when aktiv - Zeigt nur noch Fehler/Warnungen im Terminal
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 2. FileHandler für dauerhafte Speicherung
        file_handler = logging.FileHandler("logs/bank_api.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

logger = get_bank_logger()