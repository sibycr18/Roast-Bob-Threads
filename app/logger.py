import logging
import coloredlogs

# Custom color scheme
CUSTOM_LEVEL_STYLES = {
    'info': {'color': 'green', 'bold': True},
    'warning': {'color': 'yellow', 'bold': True},
    'error': {'color': 'red', 'bold': True, 'background': 'black'},
    'critical': {'color': 'red', 'bold': True, 'background': 'black', 'decoration': 'blink'},
    'debug': {'color': 'blue', 'bold': True}
}

CUSTOM_FIELD_STYLES = {
    'asctime': {'color': 'magenta'},
    'hostname': {'color': 'magenta'},
    'levelname': {'color': 'cyan', 'bold': True},
    'name': {'color': 'blue'},
    'programname': {'color': 'cyan'}
}

# Set up coloredlogs with custom formatting and colors
coloredlogs.install(
    level='INFO',
    fmt='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level_styles=CUSTOM_LEVEL_STYLES,
    field_styles=CUSTOM_FIELD_STYLES
)

# Create a logger instance
logger = logging.getLogger(__name__)

def log_info(message: str):
    """
    Log an informational message.

    Args:
        message (str): The message to log.
    """
    logging.info(message)

def log_error(message: str):
    """
    Log an error message.

    Args:
        message (str): The message to log.
    """
    logging.error(message)
