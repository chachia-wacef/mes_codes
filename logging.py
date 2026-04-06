# Dans chaque fichier (main.py, utils.py, api.py...)
import logging
logger = logging.getLogger(__name__)
# En utilisant __name__, le logger prend automatiquement le nom du module (ex: utils, processing.api, etc.).


# ou
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(name)s] | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)