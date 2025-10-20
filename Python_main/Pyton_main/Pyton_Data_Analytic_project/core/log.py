import logging
import sys

# Настраиваем базовый логгер для вывода в консоль
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Создаем псевдонимы для удобства использования в проекте
logger = logging.getLogger(__name__)


def print_info(message):
    print(f"[INFO] {message}")
    """Логирует информационное сообщение."""
    logger.info(message)


def print_success(message):
    print(f"[SUCCESS] {message}")
    """Логирует сообщение об успехе (используя уровень INFO с эмодзи)."""
    logger.info(f"✅ {message}")


def print_error(message):
    print(f"[ERROR] {message}")
    """Логирует сообщение об ошибке."""
    logger.error(message)
