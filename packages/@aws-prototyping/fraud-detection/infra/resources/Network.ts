import {Construct} from "constructs";
import {FlowLog, FlowLogDestination, FlowLogResourceType, IpAddresses, SubnetType, Vpc} from "aws-cdk-lib/aws-ec2";
import {Role, ServicePrincipal} from "aws-cdk-lib/aws-iam";
import {LogGroup} from "aws-cdk-lib/aws-logs";

export interface NetworkConstructProps {

}

export class NetworkConstruct extends Construct {
    public readonly vpc: Vpc;


    constructor(scope: Construct, id: string, props: NetworkConstructProps) {
        super(scope, id);

        const logGroup = new LogGroup(this, `${id}-vpc-logs`);

        const flowLogRole = new Role(this, `${id}-vpc-flow-log-role`, {
            assumedBy: new ServicePrincipal('vpc-flow-logs.amazonaws.com')
        });

        logGroup.grantWrite(flowLogRole)

        const prefix = scope.node.id
        this.vpc = new Vpc(this, `${prefix}FraudDetectionVpc`, {
            ipAddresses: IpAddresses.cidr("10.0.0.0/16"),
            maxAzs: 2,
            vpcName: `${prefix}-fd-vpc`,
            natGateways: 1
        });

        new FlowLog(this, 'FlowLog', {
            resourceType: FlowLogResourceType.fromVpc(this.vpc),
            destination: FlowLogDestination.toCloudWatchLogs(logGroup, flowLogRole)
        });

    }
}
