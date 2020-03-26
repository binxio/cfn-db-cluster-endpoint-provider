import uuid
import botocore
from botocore.stub import Stubber, ANY
from db_cluster_endpoint_provider import DBClusterEndpointProvider

provider = DBClusterEndpointProvider()
provider.sleep_period_in_seconds = 0.1

def test_create_endpoint():

    request = Request(
        "Create",
        properties = {
            "DBClusterIdentifier": "aurora",
            "DBClusterEndpointIdentifier": "readers",
            "EndpointType": "READER",
            "StaticMembers": ["instance1"],
        },
    )
    rds = botocore.session.get_session().create_client(
        "rds", region_name="eu-central-1"
    )
    stubber = Stubber(rds)
    stubber.add_response(
        "create_db_cluster_endpoint",
        CreateDbClusterEndpointReponse(request),
        request["ResourceProperties"],
    )
    stubber.add_response(
        "describe_db_cluster_endpoints",
        DescribeDBClusterEndpointReponse(request, "creating"),
        {"DBClusterEndpointIdentifier": "readers"},
    )
    stubber.add_response(
        "describe_db_cluster_endpoints",
        DescribeDBClusterEndpointReponse(request, "available"),
        {"DBClusterEndpointIdentifier": "readers"},
    )
    stubber.activate()
    provider.rds = rds

    response = provider.handle(request, ())
    assert response["Status"] == "SUCCESS", response["Reason"]
    stubber.assert_no_pending_responses()

def test_update_endpoint():

    request = Request(
        "Update",
        properties = {
            "DBClusterIdentifier": "aurora",
            "DBClusterEndpointIdentifier": "readers",
            "EndpointType": "READER",
            "StaticMembers": ["instance2"],
        },
        old_properties = {
            "DBClusterIdentifier": "aurora",
            "DBClusterEndpointIdentifier": "readers",
            "EndpointType": "READER",
            "StaticMembers": ["instance1"],
        },
    )
    rds = botocore.session.get_session().create_client(
        "rds", region_name="eu-central-1"
    )
    stubber = Stubber(rds)
    stubber.add_response(
        "modify_db_cluster_endpoint",
        CreateDbClusterEndpointReponse(request),
        {'DBClusterEndpointIdentifier': 'readers', 'StaticMembers': ['instance2']},
    )
    stubber.add_response(
        "describe_db_cluster_endpoints",
        DescribeDBClusterEndpointReponse(request, "modifying"),
        {"DBClusterEndpointIdentifier": "readers"},
    )
    stubber.add_response(
        "describe_db_cluster_endpoints",
        DescribeDBClusterEndpointReponse(request, "available"),
        {"DBClusterEndpointIdentifier": "readers"},
    )
    stubber.activate()
    provider.rds = rds

    response = provider.handle(request, ())
    assert response["Status"] == "SUCCESS", response["Reason"]
    stubber.assert_no_pending_responses()

def test_invalid_update_endpoint():

    request = Request(
        "Update",
        properties = {
            "DBClusterIdentifier": "aurora-2",
            "DBClusterEndpointIdentifier": "readers-1",
            "EndpointType": "WRITER",
            "StaticMembers": ["instance2"],
            "Tags": [{"Key": "Name", "Value": "writer"}]
        },
        old_properties = {
            "DBClusterIdentifier": "aurora",
            "DBClusterEndpointIdentifier": "readers",
            "EndpointType": "READER",
            "StaticMembers": ["instance1"],
        },
    )
    rds = botocore.session.get_session().create_client(
        "rds", region_name="eu-central-1"
    )
    stubber = Stubber(rds)
    stubber.activate()
    provider.rds = rds

    response = provider.handle(request, ())
    assert response["Status"] == "FAILED", response["Reason"]
    assert response["Reason"] == 'these properties cannot be updated: DBClusterEndpointIdentifier, DBClusterIdentifier, Tags'
    stubber.assert_no_pending_responses()

def test_delete_endpoint():

    request = Request(
        "Delete",
        properties = {
            "DBClusterIdentifier": "aurora",
            "DBClusterEndpointIdentifier": "readers",
            "EndpointType": "READER",
            "StaticMembers": ["instance2"],
        },
    )
    rds = botocore.session.get_session().create_client(
        "rds", region_name="eu-central-1"
    )
    stubber = Stubber(rds)
    stubber.add_response(
        "delete_db_cluster_endpoint",
        CreateDbClusterEndpointReponse(request),
        {'DBClusterEndpointIdentifier': 'readers'},
    )
    stubber.add_response(
        "describe_db_cluster_endpoints",
        DescribeDBClusterEndpointReponse(request, "deleting"),
        {"DBClusterEndpointIdentifier": "readers"},
    )
    stubber.add_response(
        "describe_db_cluster_endpoints",
        DescribeDBClusterEndpointReponse(request, status=None),
        {"DBClusterEndpointIdentifier": "readers"},
    )
    stubber.activate()
    provider.rds = rds

    response = provider.handle(request, ())
    assert response["Status"] == "SUCCESS", response["Reason"]
    stubber.assert_no_pending_responses()



class Request(dict):
    def __init__(self, request_type, properties:dict, old_properties:dict = {}, physical_resource_id=None):
        request_id = "request-%s" % uuid.uuid4()
        self.update(
            {
                "RequestType": request_type,
                "ResponseURL": "https://httpbin.org/put",
                "StackId": "arn:aws:cloudformation:us-west-2:EXAMPLE/stack-name/guid",
                "RequestId": request_id,
                "ResourceType": "Custom::DBClusterEndpoint",
                "LogicalResourceId": "Endpoint",
                "ResourceProperties": properties,

            }
        )
        if physical_resource_id:
            self["PhysicalResourceId"] = physical_resource_id
        elif request_type != "Create":
            self["PhysicalResourceId"] = f"arn:aws:rds:eu-central-1:123456789012:{properties['DBClusterIdentifier']}:{properties['DBClusterEndpointIdentifier']}"

        if request_type == "Update":
            self["OldResourceProperties"] = old_properties if old_properties else {}


class CreateDbClusterEndpointReponse(dict):
    def __init__(self, request):
        status = {"Create": "creating", "Update": "modifying", "Delete": "deleting"}

        self["ResponseMetadata"] = {
            "RequestId": request["RequestId"],
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "2c7bd3fe-730c-4d24-b9a5-1942193a091a",
                "content-type": "text/xml",
                "content-length": "275",
                "date": "Sat, 16 Nov 2019 17:58:29 GMT",
            },
            "RetryAttempts": 0,
        }
        properties = request["ResourceProperties"]
        self.update(
            {
                "DBClusterEndpointIdentifier": properties["DBClusterEndpointIdentifier"],
                "DBClusterIdentifier": properties["DBClusterIdentifier"],
                "DBClusterEndpointResourceIdentifier": f"request['DBClusterEndpointIdentifier']-ANPAJ4AE5446DAEXAMPLE",
                "Endpoint": f"{properties['DBClusterEndpointIdentifier']}.{properties['DBClusterIdentifier']}.eu-central-1.rds.amazonaws.com",
                "Status": status[request["RequestType"]],
                "EndpointType": "CUSTOM",
                "CustomEndpointType": properties["EndpointType"],
                "StaticMembers": properties.get("StaticMembers", []),
                "ExcludedMembers": properties.get("ExcludedMembers", []),
                "DBClusterEndpointArn": f"arn:aws:rds:eu-central-1:123456789012:{properties['DBClusterIdentifier']}:{properties['DBClusterEndpointIdentifier']}",
            }
        )


class DescribeDBClusterEndpointReponse(dict):
    def __init__(self, request, status=None):
        self["ResponseMetadata"] = {
            "RequestId": request["RequestId"],
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "2c7bd3fe-730c-4d24-b9a5-1942193a091a",
                "content-type": "text/xml",
                "content-length": "275",
                "date": "Sat, 16 Nov 2019 17:58:29 GMT",
            },
            "RetryAttempts": 0,
        }
        properties = request["ResourceProperties"]
        if status:
            self.update(
                {
                    "DBClusterEndpoints": [
                        {
                            "DBClusterIdentifier": properties["DBClusterIdentifier"],
                            "Endpoint": f"{properties['DBClusterEndpointIdentifier']}.{properties['DBClusterIdentifier']}.eu-central-1.rds.amazonaws.com",
                            "Status": status,
                            "EndpointType": properties["EndpointType"],
                        }
                    ]
                }
            )
        else:
            self.update({ "DBClusterEndpoints": []})
