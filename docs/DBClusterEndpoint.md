# Custom::DBClusterEndpoint
The `Custom::DBClusterEndpoint` manages an Aurora DB Cluster Endpoint.

## Syntax
To declare this entity in your AWS CloudFormation template, use the following syntax:

```yaml
Resources:
  ClusterEndpoint:
    Type: Custom::DBClusterEndpoint
    Properties:
        DBClusterIdentifier: String
        DBClusterEndpointIdentifier: String
        EndpointType: 'READER|WRITER|ANY'
        StaticMembers:
          - ''
        ExcludedMembers:
          - ''
        Tags:
          - Key: ''
            Value: ''

        ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-db-cluster-endpoint-provider'
        
Outputs:
    Arn:
        Value: !GetAtt ClusterEndpoint.Arn
    Endpoint:
        Value: !GetAtt ClusterEndpoint.Endpoint
```


## Properties
You can specify the same properties as the [CreateDBClusterEndpoint](https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/API_CreateDBClusterEndpoint.html) 
api call.

Note that `Tags` cannot be updated in the [ModifyBClusterEndpoint](https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/API_ModifyDBClusterEndpoint.html) 
api call. I recommend you use the [Custom::Tag](https://github.com/binxio/cfn-tag-provider) instead.

## Return values
With 'Fn::GetAtt' the following values are available:

- `Arn` - The ARN of the endpoint.
- `Endpoint` - the DNS name of the endpoint.