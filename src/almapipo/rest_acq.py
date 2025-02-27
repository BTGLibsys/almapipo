"""
Query the Alma API for vendors
"""

from logging import getLogger

from . import setup_rest

# Logfile
logger = getLogger(__name__)


class VendorsApi(setup_rest.GenericApi):
    """
    Make calls for acq records.
    """
    def __init__(self):
        """
        Initialize API calls for bibliographic records.
        """
        base_path = "/acq/vendors/"

        logger.info(f"Instantiating {type(self).__name__}.")

        super().__init__(base_path)
