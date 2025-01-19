import { Construct } from "constructs";
import {
  IVpc,
  Peer,
  Port,
  SecurityGroup,
  SubnetType,
} from "aws-cdk-lib/aws-ec2";
import { IBucket } from "aws-cdk-lib/aws-s3";
import {
  ArnPrincipal,
  Effect,
  PolicyDocument,
  PolicyStatement,
  Role,
  ServicePrincipal,
} from "aws-cdk-lib/aws-iam";
import {
  DockerImageAsset,
  NetworkMode,
  Platform,
} from "aws-cdk-lib/aws-ecr-assets";
import * as efs from "aws-cdk-lib/aws-efs";
import {
  Cluster,
  ContainerImage,
  CpuArchitecture,
  FargateService,
  FargateTaskDefinition,
  LogDriver,
  OperatingSystemFamily,
  Protocol,
} from "aws-cdk-lib/aws-ecs";
import { CfnOutput, Duration, Stack } from "aws-cdk-lib";
import { Topic } from "aws-cdk-lib/aws-sns";
import {
  CfnIdentityPool,
  UserPool,
  UserPoolClient,
  UserPoolDomain,
} from "aws-cdk-lib/aws-cognito";
import * as elb from "aws-cdk-lib/aws-elasticloadbalancingv2";
import {
  ListenerAction,
  ListenerCondition,
} from "aws-cdk-lib/aws-elasticloadbalancingv2";
import { Secret } from "aws-cdk-lib/aws-secretsmanager";
import {
  AllowedMethods,
  CachePolicy,
  Distribution,
  OriginProtocolPolicy,
  OriginRequestCookieBehavior,
  OriginRequestHeaderBehavior,
  OriginRequestPolicy,
  OriginRequestQueryStringBehavior,
  ViewerProtocolPolicy,
} from "aws-cdk-lib/aws-cloudfront";
import { LoadBalancerV2Origin } from "aws-cdk-lib/aws-cloudfront-origins";
import { Table } from "aws-cdk-lib/aws-dynamodb";
import { AuthenticateCognitoAction } from "aws-cdk-lib/aws-elasticloadbalancingv2-actions";
import { CfnDomain } from "aws-cdk-lib/aws-opensearchservice";
import path = require("path");
import { CfnAccessPolicy } from "aws-cdk-lib/aws-opensearchserverless";

import { Lambda } from "aws-cdk-lib/aws-ses-actions";
import { LambdaRestApi } from "aws-cdk-lib/aws-apigateway";
import { CfnCollection } from "aws-cdk-lib/aws-opensearchserverless";
import { StringParameter } from "aws-cdk-lib/aws-ssm";
import { AwsManagedPrefixList } from "../lib/util/aws-managed-prefix-list";
import { FraudDetectionApiProps } from "./Api";

export interface AppConstructProps extends FraudDetectionApiProps {
  readonly api: LambdaRestApi;
}
const CLOUDFRONT_CUSTOM_HEADER = "x-cf-origin";

export class AppFargateConstruct extends Construct {
  public readonly loadBalancer: elb.ApplicationLoadBalancer;

  constructor(scope: Construct, id: string, props: AppConstructProps) {
    super(scope, id);

    const { vpc, indexedFileTable } = props;

    const cluster = new Cluster(this, `${id}AppCluster`, {
      vpc,
      containerInsights: true,
      enableFargateCapacityProviders: true,
    });
    const fileSystemName = `${id}AppFileSystem`;
    const fileSystem = new efs.FileSystem(this, `${id}AppFileSystem`, {
      vpc,
      fileSystemName,
      lifecyclePolicy: efs.LifecyclePolicy.AFTER_30_DAYS, // files are not accessed for 14 days will be moved to EFS Infrequent Access
      performanceMode: efs.PerformanceMode.GENERAL_PURPOSE, // default, good for a broad spectrum of use cases
      outOfInfrequentAccessPolicy:
        efs.OutOfInfrequentAccessPolicy.AFTER_1_ACCESS,
    });

    const efsPolicy = new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        "elasticfilesystem:ClientMount",
        "elasticfilesystem:ClientWrite",
        "elasticfilesystem:ClientRootAccess",
      ],
      resources: [fileSystem.fileSystemArn], // Assuming `fileSystem` is the EFS resource from above
    });

    props.ecsAppRole.addToPolicy(efsPolicy);

    const asgTopic = new Topic(this, `${id}asgAppTopic`);

    props.ecsAppRole.addToPolicy(
      new PolicyStatement({
        effect: Effect.ALLOW,
        resources: ["*"],
        actions: [
          "bedrock:*",
          "ecs:CreateCluster",
          "ecs:DeregisterContainerInstance",
          "ecs:DiscoverPollEndpoint",
          "ecs:Poll",
          "ecs:RegisterContainerInstance",
          "ecs:StartTelemetrySession",
          "ecs:Submit*",
          "ssm:*",
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "ec2:AuthorizeSecurityGroupIngress",
          "ec2:Describe*",
          "cognito-identity:*",
          "cognito-idp:*",
          "rekognition:DetectLabels",
          "sagemaker:*",
          "elasticloadbalancing:DeregisterInstancesFromLoadBalancer",
          "elasticloadbalancing:DeregisterTargets",
          "elasticloadbalancing:Describe*",
          "elasticloadbalancing:RegisterInstancesWithLoadBalancer",
          "elasticloadbalancing:RegisterTargets",
          "aoss:*",
          "geo:*",
        ],
      })
    );

    props.ecsAppRole.addToPrincipalPolicy(
      new PolicyStatement({
        effect: Effect.ALLOW,
        actions: ["execute-api:Invoke"],
        resources: [
          `arn:aws:execute-api:${Stack.of(this).region}:${Stack.of(this).account}:${props.api.restApiId}/*/*/*`,
        ],
      })
    );

    props.storageBucket.grantReadWrite(props.ecsAppRole);
    props.logsBucket.grantReadWrite(props.ecsAppRole);
    asgTopic.grantPublish(props.ecsAppRole);
    props.SerpApiKeySecret.grantRead(props.ecsAppRole);
    indexedFileTable.grantReadWriteData(props.ecsAppRole);

    const sg = new SecurityGroup(this, `${id}sgapp`, {
      vpc: props.vpc,
      allowAllOutbound: true,
      securityGroupName: `${id}AppSecurityGroup`,
    });
    sg.addIngressRule(Peer.ipv4(vpc.vpcCidrBlock), Port.tcp(8501));
    sg.addIngressRule(
      Peer.ipv4(vpc.vpcCidrBlock),
      Port.tcp(2049), // NFS traffic
      "allow NFS traffic from within the VPC"
    );
    fileSystem.connections.addSecurityGroup(sg);

    const imageAsset = new DockerImageAsset(this, `${id}AppImageAsset`, {
      directory: path.join(__dirname, "../../app/"),
      file: "app.dockerfile",
      platform: Platform.LINUX_ARM64,
      networkMode: NetworkMode.HOST,
      invalidation: {
        platform: true,
      },
    });

    const taskDefinition = new FargateTaskDefinition(
      this,
      `${id}AppTaskDefinition`,
      {
        taskRole: props.ecsAppRole,
        executionRole: props.ecsRole,
        cpu: 8192,
        memoryLimitMiB: 32768,
        runtimePlatform: {
          cpuArchitecture: CpuArchitecture.ARM64,
          operatingSystemFamily: OperatingSystemFamily.LINUX,
        },
      }
    );

    taskDefinition.addVolume({
      name: `${id}efs-volume`,
      efsVolumeConfiguration: {
        fileSystemId: fileSystem.fileSystemId,
      },
    });

    const cf_dist_ssm_parameter_name = "/fraud-detection/cloudfront-endpoint";

    const container = taskDefinition.addContainer(`${id}AppContainer`, {
      image: ContainerImage.fromDockerImageAsset(imageAsset), // replace with your image repository and tag
      memoryLimitMiB: 24576,
      cpu: 8192,
      environment: {
        SERP_API_KEY_SECRET: props.SerpApiKeySecret.secretName,
        POOL_ID: props.userPool.userPoolId,
        APP_CLIENT_ID: props.userPoolClient.userPoolClientId,
        APP_CLIENT_SECRET:
          props.userPoolClient.userPoolClientSecret.unsafeUnwrap(),
        IDENTITY_POOL_ID: props.identityPool.ref,
        AWS_DEFAULT_REGION: Stack.of(this).region,
        AWS_ACCOUNT_ID: Stack.of(this).account,
        STORAGE_BUCKET: props.storageBucket.bucketName,
        INDEXED_FILES_TABLE: indexedFileTable.tableName,
        OPENSEARCH_DOMAIN: props.openSearchCollection.attrCollectionEndpoint,
        TEMP_OPENSEARCH_DOMAIN:
          props.tempOpenSearchCollection.attrCollectionEndpoint,
        API_ENDPOINT: props.api.url,
        SM_ENDPOINT_NAME_SSM_PARAMETER:
          props.sagemakerEndpointNameSsmParameter.parameterName,
        VECTOR_INDEX_NAME: "img-vector",
        TEMP_VECTOR_INDEX_NAME: "img-vector",
        COGNITO_REDIRECT_URL: `https://${props.userPoolDomain.domainName}/oauth2/idpresponse`,
        CLOUDFRONT_DIST_SSM_PARAMETER_NAME: cf_dist_ssm_parameter_name,
        COGNITO_DOMAIN: `https://${props.userPoolDomain.domainName}.auth.ap-southeast-2.amazoncognito.com`,
      },
      logging: LogDriver.awsLogs({ streamPrefix: "FraudDetectionApp" }),
      portMappings: [
        {
          containerPort: 8501,
          hostPort: 8501,
          protocol: Protocol.TCP,
        },
      ],
    });

    container.addMountPoints({
      sourceVolume: `${id}efs-volume`,
      containerPath: "/mnt/efs",
      readOnly: false,
    });

    const ecsService = new FargateService(this, `${id}AppService`, {
      cluster: cluster,
      taskDefinition: taskDefinition,
      desiredCount: 1,
      assignPublicIp: true,
      securityGroups: [sg],
    });

    fileSystem.connections.allowDefaultPortFrom(ecsService);

    // Allow only cloudfront origin-facing prefix lists to hit the load balancer
    const cfOriginFacingPrefixList = new AwsManagedPrefixList(
      this,
      "CfOriginPrefixList",
      {
        name: "com.amazonaws.global.cloudfront.origin-facing",
      }
    ).prefixList;

    // Create a load balancer
    this.loadBalancer = new elb.ApplicationLoadBalancer(this, `${id}lbApp`, {
      vpc,
      internetFacing: true,
      securityGroup: sg,
      vpcSubnets: { subnetType: SubnetType.PUBLIC },
    });

    this.loadBalancer.connections.allowFrom(
      Peer.prefixList(cfOriginFacingPrefixList.prefixListId),
      Port.tcp(8501)
    );

    const targetGroup = new elb.ApplicationTargetGroup(this, `${id}tgApp`, {
      targets: [ecsService],
      port: 8501, // Use the same port as specified in the Docker container
      protocol: elb.ApplicationProtocol.HTTP,
      vpc,
      stickinessCookieDuration: Duration.days(1),
      healthCheck: {
        enabled: true,
        interval: Duration.seconds(30),
        timeout: Duration.seconds(5),
        port: "8501",
        protocol: elb.Protocol.HTTP,
        path: "/_stcore/health",
        unhealthyThresholdCount: 5,
      },
    });

    // Create a listener for the load balancer
    const listener = this.loadBalancer.addListener(`${id}listenerApp`, {
      port: 8501,
      protocol: elb.ApplicationProtocol.HTTP,
      defaultTargetGroups: [targetGroup],
    });

    // Create a custom header value
    const customHeaderValue = new Secret(this, "CloudfrontCustomHeaderValue", {
      generateSecretString: {
        excludePunctuation: true,
        passwordLength: 64,
      },
    }).secretValue.unsafeUnwrap();

    // Ensure the ALB only accepts connections from our cloudfront distribution by verifying the custom header
    // See: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/restrict-access-to-load-balancer.html
    listener.addAction("VerifyCustomHeader", {
      conditions: [
        ListenerCondition.httpHeader(CLOUDFRONT_CUSTOM_HEADER, [
          customHeaderValue,
        ]),
      ],
      action: ListenerAction.forward([targetGroup]),
      priority: 1,
    });
    listener.addAction("TrafficWithoutHeader", {
      action: ListenerAction.fixedResponse(403),
    });

    const origin = new LoadBalancerV2Origin(this.loadBalancer, {
      httpPort: 8501,
      protocolPolicy: OriginProtocolPolicy.HTTP_ONLY,
      customHeaders: {
        [CLOUDFRONT_CUSTOM_HEADER]: customHeaderValue,
      },
    });

    // Ensure headers and query strings are passed on to the origin (ie to the load balancer + container)
    // Define an origin request policy to forward all headers and query strings to the origin
    const originRequestPolicy = new OriginRequestPolicy(
      this,
      "OriginRequestPolicy",
      {
        headerBehavior: OriginRequestHeaderBehavior.all(), // Forward all headers
        queryStringBehavior: OriginRequestQueryStringBehavior.all(), // Forward all query strings
      }
    );

    // Define the behavior for the CloudFront distribution
    const behaviour = {
      allowedMethods: AllowedMethods.ALLOW_ALL, // Allow all HTTP methods
      originRequestPolicy, // Use the defined origin request policy
    };

    /**
     * Creates an OriginRequestPolicy for WebSocket connections.
     *
     * This policy is necessary for a Streamlit app to handle WebSocket connections properly.
     * Streamlit uses WebSockets for real-time communication between the server and the client.
     *
     * The policy:
     * - Does not forward cookies to the origin.
     * - Allows specific WebSocket headers to be forwarded to the origin.
     * - Does not forward query strings to the origin.
     *
     * @param id - The unique identifier for the policy.
     */
    const wsOriginRequestPolicy = new OriginRequestPolicy(
      this,
      `${id}webSocketPolicy`,
      {
        originRequestPolicyName: `${id}webSocketPolicy`, // Name of the WebSocket policy
        comment: "A default WebSocket policy", // Comment for the policy
        cookieBehavior: OriginRequestCookieBehavior.none(), // Do not forward cookies
        headerBehavior: OriginRequestHeaderBehavior.allowList(
          "Sec-WebSocket-Key",
          "Sec-WebSocket-Version",
          "Sec-WebSocket-Protocol",
          "Sec-WebSocket-Accept"
        ), // Forward specific WebSocket headers
        queryStringBehavior: OriginRequestQueryStringBehavior.none(), // Do not forward query strings
      }
    );

    const distribution = new Distribution(this, `${id}appDistribution`, {
      defaultBehavior: {
        origin: origin,
        originRequestPolicy: wsOriginRequestPolicy,
        allowedMethods: AllowedMethods.ALLOW_ALL,
        viewerProtocolPolicy: ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: CachePolicy.CACHING_DISABLED,
      },
    });

    distribution.addBehavior("/*", origin, behaviour);

    distribution.node.addDependency(this.loadBalancer);

    // Create an SSM string parameter
    const ssmParameter = new StringParameter(this, `${id}SsmParameter`, {
      parameterName: cf_dist_ssm_parameter_name,
      stringValue: `https://${distribution.distributionDomainName}/`,
    });

    ssmParameter.node.addDependency(distribution);

    ssmParameter.grantRead(props.ecsAppRole);

    new CfnOutput(this, `${id}appDnsName`, {
      value: this.loadBalancer.loadBalancerDnsName,
    });

    new CfnOutput(this, `${id}appDistributionName`, {
      value: distribution.distributionDomainName,
    });

    new CfnOutput(this, `${id}appDistributionEndpoint`, {
      value: `https://${distribution.distributionDomainName}/`,
    });
  }
}
