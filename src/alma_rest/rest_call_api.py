"""Making consistent API calls

Basic definitions for requests sent to the Alma API, including:
* Base URL
* API Key
* Headers

There is one function to define what every session for Alma should look like.

Then for each REST operation (POST, GET, PUT, DELETE) there is one base
function that the more specific modules (like rest_bibs) can make use of.
"""

from logging import getLogger
from os import environ
from requests import Session, Response
from urllib import parse

# noinspection PyUnresolvedReferences
from . import logfile_setup

# Logfile
logger = getLogger(__name__)

api_key = environ['ALMA_REST_API_KEY']
api_base_url = environ['ALMA_REST_API_BASE_URL']


class GenericApi:
    """
    Make generic calls to an API that supports all aspects of CRUD.
    """
    def __init__(self, base_path: str):
        """
        Initialize API calls.
        :param base_path: Path used for API calls
        """
        self.base_path = base_path

    def create(self, record_data: bytes, url_parameters: dict = None) -> str:
        """
        Generic function for POST calls to the Alma API.

        Will return the response if HTTP status code is 200.
        Otherwise the error returned by the API will be added to the
        logfile as an ERROR.
        :param record_data: XML of the record to be created
        :param url_parameters: Use if you need to add parameters to the URL
        :return: Response data in XML format
        """
        logger.info(f"Trying POST for {self.base_path}.")
        if url_parameters:
            add_parameters(self.base_path, url_parameters)
        response_content = call_api(self.base_path, 'POST', 200, record_data)
        return response_content

    def delete(self, record_id: str, url_parameters: dict = None) -> str:
        """
        Generic function for DELETE calls to the Alma API.

        Will return the response if HTTP status code is 204.
        Otherwise the error returned by the API will be added to the
        logfile as an ERROR.
        
        Usually the response *should* be empty, but in case it
        is not, we might want to have access to it.
        :param record_id: Unique ID of Alma BIB records
        :param url_parameters: Use if you need to add parameters to the URL
        :return: API response
        """
        logger.info(f"Trying DELETE for record {record_id} at {self.base_path}.")
        if url_parameters:
            add_parameters(self.base_path, url_parameters)
        delete_response = call_api(f'{self.base_path}{record_id}', 'DELETE', 204)
        return delete_response

    def retrieve(self, record_id: str, url_parameters: dict = None) -> str:
        """
        Generic function for GET calls to the Alma API.

        Will return the response content if HTTP status code is 200.
        Otherwise the error returned by the API will be added to the
        logfile as an ERROR.
        :param record_id: Unique ID of an Alma BIB record
        :param url_parameters: Use if you need to add parameters to the URL
        :return: Record data of the bib record
        """
        logger.info(f"Trying GET for record {record_id} at {self.base_path}.")
        if url_parameters:
            add_parameters(self.base_path, url_parameters)
        response_content = call_api(f'{self.base_path}{record_id}', 'GET', 200)
        return response_content

    def update(self, record_id: str, record_data: bytes, url_parameters: dict = None) -> str:
        """
        Generic function for PUT calls to the Alma API.

        Will return the response if HTTP status code is 200.
        Otherwise the error returned by the API will be added to the
        logfile as an ERROR.
        :param record_data: XML of the record to be updated
        :param record_id: Unique ID of the BIB record
        :param url_parameters: Use if you need to add parameters to the URL
        :return: Response data in XML format
        """
        logger.info(f"Trying PUT for record {record_id} at {self.base_path}.")
        if url_parameters:
            add_parameters(self.base_path, url_parameters)
        response_content = call_api(f'{self.base_path}{record_id}', 'PUT', 200, record_data)
        return response_content


def add_parameters(url: str, parameters: dict):
    logger.info(f"Additional parameters provided: {parameters}.")
    url_parameters = parse.urlencode(parameters)
    url += f"?{url_parameters}"


def call_api(url_parameters: str, method: str, status_code: int, record_data: bytes = None) -> str:
    """
    Generic function for all API calls.

    Will return the response if the HTTP status code is met.
    Otherwise the error returned by the API will be added to the
    logfile as an ERROR.

    Additionally there is a check for responses that meet the
    required HTTP status code, but still contain an error. In this
    case the response will be saved to the database (if it exists),
    and the error will be added to the logfile as an ERROR.

    :param url_parameters: Necessary path and arguments for the API call.
    :param method: DELETE, GET, POST or PUT
    :param status_code: Status code of a successful API call for the given method.
    :param record_data: Necessary input for POST and PUT, defaults to None.
    :return: The API response's content in XML format as a string.
    """
    with create_alma_api_session('xml') as session:
        alma_url = api_base_url+url_parameters
        alma_response = switch_api_method(alma_url, method, session, record_data)

        if alma_response.status_code == status_code:
            alma_response_content = alma_response.content.decode("utf-8")
            logger.info(
                f'{method} for record "{url_parameters}" completed.'
            )
            if '<errorList>' in alma_response_content:
                log_string = f"""The response contained an error, even though it had status code {status_code}. """
                log_string += f"""Reason: {alma_response.status_code} - {alma_response.content}"""
                logger.warning(log_string)
            elif not alma_response_content.startswith('<?xml') and status_code != 204:
                log_string = f"""The response retrieved does not seem to be valid xml - startswith('<?xml') -- """
                log_string += {alma_response_content}
                logger.error(log_string)
            return alma_response_content

        error_string = f"""{method} for record "{url_parameters}" failed. """
        error_string += f"""Reason: {alma_response.status_code} - {alma_response.content.decode("utf-8")}"""
        logger.error(error_string)


def switch_api_method(alma_url: str, method: str, session: Session, record_data: str = None) -> Response:
    """
    Make API calls according to the kind of method provided.
    :param alma_url: Combination of base-url and parameters necessary (path, arguments).
    :param method: DELETE, GET, POST or PUT
    :param session: Alma API session.
    :param record_data: Necessary input for POST and PUT, defaults to None.
    :return:
    """
    if method == 'DELETE':
        return session.delete(alma_url)
    elif method == 'GET':
        return session.get(alma_url)
    elif method == 'POST':
        return session.post(alma_url, data=record_data)
    elif method == 'PUT':
        return session.put(alma_url, data=record_data)
    logger.error('No valid REST method supplied.')
    raise ValueError


def create_alma_api_session(session_format) -> Session:
    """Create a Session with parameters from env vars
    :param session_format: Format in which records are sent and retrieved.
    :return: Session object for connections to Alma
    """
    session = Session()
    session.headers.update({
        "accept": "application/" + session_format,
        "Content-Type": "application/" + session_format,
        "authorization": f"apikey {api_key}",
        "User-Agent": "alma_rest/0.0.1"
    })
    return session
