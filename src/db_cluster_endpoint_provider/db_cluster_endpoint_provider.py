from cfn_resource_provider import ResourceProvider
from copy import copy
import boto3
from .logger import log
from time import sleep
from botocore.exceptions import ClientError

request_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "DBClusterIdentifier": {"type": "string", "pattern": "[a-z0-9\\-_]+"},
        "DBClusterEndpointIdentifier": {"type": "string", "pattern": "[a-z0-9\\-_]+"},
        "EndpointType": {"type": "string", "enum": ["READER", "WRITER", "ANY"]},
        "StaticMembers": {"type": "array", "items": [{"type": "string"}]},
        "ExcludedMembers": {"type": "array", "items": [{"type": "string"}]},
        "Tags": {
            "type": "array",
            "items": [
                {
                    "type": "object",
                    "properties": {
                        "Key": {"type": "string"},
                        "Value": {"type": "string"},
                    },
                    "required": ["Key", "Value"],
                }
            ],
        },
    },
    "required": ["DBClusterIdentifier", "DBClusterEndpointIdentifier", "EndpointType"],
}


class DBClusterEndpointProvider(ResourceProvider):
    def __init__(self):
        super(DBClusterEndpointProvider, self).__init__()
        self.sleep_period_in_seconds = 5
        self.request_schema = request_schema
        self.rds = boto3.client("rds")
        self.updatable_properties = set(
            ["EndpointType", "StaticMembers", "ExcludedMembers"]
        )

    def wait_until_completed(self, response, status: str) -> bool:
        arn = response["DBClusterEndpointArn"]
        db_cluster_endpoint_identifier = response["DBClusterEndpointIdentifier"]

        while response["Status"] == status:
            log.info(
                "cluster endpoint %s is in state %s, waiting %ss",
                arn,
                response["Status"],
                self.sleep_period_in_seconds
            )
            sleep(self.sleep_period_in_seconds)
            endpoints = self.rds.describe_db_cluster_endpoints(
                DBClusterEndpointIdentifier=db_cluster_endpoint_identifier
            )
            if not endpoints["DBClusterEndpoints"]:
                if status == "deleting":
                    return True

                self.fail(
                    f"db cluster endpoint {db_cluster_endpoint_identifier} has been deleted"
                )
                return False

            response = endpoints["DBClusterEndpoints"][0]
        return True

    def create(self):
        kwargs = copy(self.properties)
        kwargs.pop("ServiceToken", None)

        response = self.rds.create_db_cluster_endpoint(**kwargs)
        self.physical_resource_id = response["DBClusterEndpointArn"]
        self.set_attribute("Endpoint", response["Endpoint"])
        self.wait_until_completed(response, "creating")

    def changed_properties(self) -> set:
        result = set()
        for k, v in self.properties.items():
            if self.old_properties.get(k) != v:
                result.add(k)
        return result

    @property
    def db_cluster_identifier(self):
        return self.get("DBClusterEndpointIdentifier")

    def update(self):
        changes = self.changed_properties()
        immutables = self.changed_properties().difference(self.updatable_properties)
        if immutables:
            self.fail(
                "these properties cannot be updated: {}".format(", ".join(sorted(immutables)))
            )
            return

        if not changes:
            self.success("no changes")
            return

        kwargs = {k: self.get(k) for k in changes}
        kwargs["DBClusterEndpointIdentifier"] = self.db_cluster_identifier

        response = self.rds.modify_db_cluster_endpoint(**kwargs)
        self.physical_resource_id = response["DBClusterEndpointArn"]
        self.set_attribute("Endpoint", response["Endpoint"])
        self.wait_until_completed(response, "modifying")

    def delete(self):
        if self.physical_resource_id == "could-not-create":
            self.success("db cluster endpoint was never created")
            return

        try:
            response = self.rds.delete_db_cluster_endpoint(
                DBClusterEndpointIdentifier=self.db_cluster_identifier
            )
            self.wait_until_completed(response, "deleting")
        except ClientError as e:
            msg = f"failed to delete db cluster endpoint {self.db_cluster_identifier}"
            log.error(
                f"failed to delete db cluster endpoint {self.db_cluster_identifier}, {e}"
            )
            self.success(msg)


provider = DBClusterEndpointProvider()


def handler(request, context):
    return provider.handle(request, context)
