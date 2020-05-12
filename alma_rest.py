"""Main point of access

This will import the other modules and do the following:
* Import a CSV or TSV file to the database tables source_csv and job_status_per_id
* Call the API with the according action (POST, GET, PUT, DELETE)
* Save the results of successful API calls to database table fetched_records
* If API calls are not successful, mark the IDs with "error" in job_status_per_id
"""

from logging import getLogger
from datetime import datetime

import db_read_write
import input_read
# noinspection PyUnresolvedReferences
import logfile_setup
import rest_bibs

# Timestamp for the Script-Run as inserted in the database
job_timestamp = datetime.now()

# Logfile
logger = getLogger(__name__)
logger.info(f"Starting {__name__} with Job-ID {job_timestamp}")


def get_records_via_api_for_csv_list(csv_path: str):
    """
    For a list of Alma-IDs given in a CSV file, this function does the following:
    * Save the data from the CSV-file to tables job_status_per_id and source_csv
    * Call GET on the Alma API for each Alma-ID
    * Save the response from the API in table fetched_records
    Note that this will only work for Alma-IDs and not alternatives like "Other system number".

    List of possible Alma-IDs:
    * MMS-ID
    * Holding-ID
    * Item-ID
    * Portfolio-ID

    :param csv_path: Path of the CSV file containing the Alma IDs.
    :return: None
    """
    db_session = db_read_write.create_db_session()
    import_csv_to_db_tables(csv_path, 'GET')
    list_of_ids = db_read_write.get_list_of_ids_for_job_with_status('new', job_timestamp, db_session)
    for alma_id, in list_of_ids:
        split_alma_id = str.split(alma_id, ',')
        id_prefix = split_alma_id[-1][0:2]
        if id_prefix == "99":
            record_data = rest_bibs.get_bib(alma_id)
        elif id_prefix == "22":
            mms_id = split_alma_id[0]
            hol_id = split_alma_id[1]
            record_data = rest_bibs.get_hol(mms_id, hol_id)
        elif id_prefix == "23":
            mms_id = split_alma_id[0]
            hol_id = split_alma_id[1]
            itm_id = split_alma_id[2]
            record_data = rest_bibs.get_item(mms_id, hol_id, itm_id)
        elif id_prefix == "53":
            mms_id = split_alma_id[0]
            portfolio_id = split_alma_id[1]
            record_data = rest_bibs.get_portfolio(mms_id, portfolio_id)
        elif id_prefix == "61":
            mms_id = split_alma_id[0]
            collection_id = split_alma_id[1]
            record_data = rest_bibs.get_e_collection(mms_id, collection_id)
        else:
            logger.error("Alma-Id does not have one of the expected prefixes (99, 22, 23 or 53).")
            record_data = None
        if record_data is None:
            db_read_write.update_job_status_for_alma_id('error', alma_id, job_timestamp, db_session)
        else:
            db_read_write.update_job_status_for_alma_id('done', alma_id, job_timestamp, db_session)
            db_read_write.add_fetched_record_to_session(alma_id, record_data, job_timestamp, db_session)
    db_session.commit()


def import_csv_to_db_tables(file_path: str, action: str = 'GET', validation: bool = True):
    """
    Imports a whole csv or tsv file to the table source_csv.
    Imports valid Alma-IDs to table job_status_per_id.
    Checks for file existence first.
    NOTE: If no action (GET, PUT, POST or DELETE) is provided,
    it will default to "GET".
    :param file_path: Path to the CSV file to be imported.
    :param action: REST action - GET, PUT, POST or DELETE, defaults to empty string.
    :param validation: If set to "False", the first column will not be checked for validity. Defaults to True.
    :return: None
    """
    if input_read.check_file_path(file_path):
        session = db_read_write.create_db_session()
        csv_generator = input_read.read_csv_contents(file_path, validation)
        for csv_line in csv_generator:
            # noinspection PyTypeChecker
            db_read_write.add_csv_line_to_session(csv_line, job_timestamp, session, action)
        session.commit()
    else:
        logger.error('No valid file path provided.')
