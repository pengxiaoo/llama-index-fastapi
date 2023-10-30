import boto3
import os
from app.utils.log_util import logger
from app.utils import data_util

IS_LOCAL_TEST = os.environ.get("IS_LOCAL_TEST")
REGION = "ap-southeast-1"
SSO_REGION = "ap-northeast-1"
SUPPORTED_RESOURCE_TYPES = ["s3", "dynamodb"]
SUPPORTED_CLIENT_TYPES = ["cognito-idp", "ses"]
RESOURCE_POOL = {}
CLIENT_POOL = {}


def get_resource(resource_type):
    logger.info(f"get_{resource_type}(): IS_LOCAL_TEST: {IS_LOCAL_TEST}")
    data_util.assert_true(resource_type in SUPPORTED_RESOURCE_TYPES, f"resource_type: {resource_type} is not supported")
    if resource_type not in RESOURCE_POOL:
        logger.warning(f"create new resource for {resource_type}")
        RESOURCE_POOL[resource_type] = boto3.resource(resource_type)
    logger.info(f"get resource for {resource_type}")
    return RESOURCE_POOL[resource_type]


def get_client(client_type):
    logger.info(f"get_{client_type}(): IS_LOCAL_TEST: {IS_LOCAL_TEST}")
    data_util.assert_true(client_type in SUPPORTED_CLIENT_TYPES, f"client_type: {client_type} is not supported")
    if client_type not in CLIENT_POOL:
        logger.warning(f"create new client for {client_type}")
        CLIENT_POOL[client_type] = boto3.client(client_type)
    logger.info(f"get client for {client_type}")
    return CLIENT_POOL[client_type]


def get_dynamodb():
    return get_resource("dynamodb")


def get_cognito_idp():
    return get_client("cognito-idp")


def get_ses():
    return get_client("ses")


def get_s3():
    return get_resource("s3")


if __name__ == "__main__":
    pass
