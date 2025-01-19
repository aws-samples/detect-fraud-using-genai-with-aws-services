import { Construct } from "constructs";
import { CfnOutput, Duration, Stack } from "aws-cdk-lib";
import {
  Architecture,
  DockerImageCode,
  DockerImageFunction,
  IFunction,
} from "aws-cdk-lib/aws-lambda";
import { Platform } from "aws-cdk-lib/aws-ecr-assets";
import * as iam from "aws-cdk-lib/aws-iam";
import * as path from "path";

import { StringParameter } from "aws-cdk-lib/aws-ssm";
import { AwsCustomResource } from "aws-cdk-lib/custom-resources";
import {
  AuthorizationType,
  CfnMethod,
  LambdaRestApi,
} from "aws-cdk-lib/aws-apigateway";
import { IVpc } from "aws-cdk-lib/aws-ec2";
import { INetworkLoadBalancer } from "aws-cdk-lib/aws-elasticloadbalancingv2";
import { Table } from "aws-cdk-lib/aws-dynamodb";
import { AnyPrincipal } from "aws-cdk-lib/aws-iam";
import { Secret } from "aws-cdk-lib/aws-secretsmanager";
import {
  CfnIdentityPool,
  UserPool,
  UserPoolClient,
  UserPoolDomain,
} from "aws-cdk-lib/aws-cognito";
import { IBucket } from "aws-cdk-lib/aws-s3";
import { CfnCollection } from "aws-cdk-lib/aws-opensearchserverless";

export interface FraudDetectionApiProps {
  readonly vpc: IVpc;
  readonly indexedFilesTable: Table;
  readonly ecsRole: iam.Role;
  readonly ecsAppRole: iam.Role;
  readonly storageBucket: IBucket;
  readonly logsBucket: IBucket;
  readonly userPool: UserPool;
  readonly userPoolClient: UserPoolClient;
  readonly userPoolDomain: UserPoolDomain;
  readonly identityPool: CfnIdentityPool;
  readonly SerpApiKeySecret: Secret;
  readonly indexedFileTable: Table;
  readonly openSearchCollection: CfnCollection;
  readonly tempOpenSearchCollection: CfnCollection;
  readonly sagemakerEndpointNameSsmParameter: StringParameter;
}

export class FraudDetectionApi extends Construct {
  readonly api: LambdaRestApi;
  readonly handler: IFunction;
  readonly fn_env_vars: Record<string, string>;
  constructor(scope: Construct, id: string, props: FraudDetectionApiProps) {
    super(scope, id);

    const { indexedFilesTable } = props;

    const handlerRole = new iam.Role(this, "HandlerRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
    });

    handlerRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:*"],
        resources: ["*"],
      })
    );
    handlerRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName(
        "service-role/AWSLambdaVPCAccessExecutionRole"
      )
    );
    handlerRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          "cloudformation:DescribeStacks",
          "cloudformation:DescribeStackEvents",
          "cloudformation:DescribeStackResource",
          "cloudformation:DescribeStackResources",
          "cloudformation:DeleteStack",
          "aoss:*",
          "geo:*",
        ],
        resources: [`*`],
      })
    );

    handlerRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          "apigateway:GET",
          "apigateway:POST",
          "apigateway:PUT",
          "apigateway:DELETE",
        ],
        resources: [`arn:aws:apigateway:${Stack.of(this).region}::/*`],
      })
    );

    props.SerpApiKeySecret.grantRead(handlerRole);
    props.storageBucket.grantReadWrite(handlerRole);
    props.logsBucket.grantReadWrite(handlerRole);
    props.SerpApiKeySecret.grantRead(handlerRole);
    props.indexedFileTable.grantReadWriteData(handlerRole);

    // Define environment variables for the Lambda function
    this.fn_env_vars = {
      ACCOUNT: Stack.of(this).account, // AWS account ID
      REGION: Stack.of(this).region, // AWS region
      INDEXED_FILES_TABLE: indexedFilesTable.tableName, // DynamoDB table name for indexed files
      SERP_API_KEY_SECRET: props.SerpApiKeySecret.secretName, // Secret name for Serp API key
      POOL_ID: props.userPool.userPoolId, // Cognito User Pool ID
      APP_CLIENT_ID: props.userPoolClient.userPoolClientId, // Cognito User Pool Client ID
      APP_CLIENT_SECRET:
        props.userPoolClient.userPoolClientSecret.unsafeUnwrap(), // Cognito User Pool Client Secret
      IDENTITY_POOL_ID: props.identityPool.ref, // Cognito Identity Pool ID
      AWS_ACCOUNT_ID: Stack.of(this).account, // AWS account ID (duplicate)
      STORAGE_BUCKET: props.storageBucket.bucketName, // S3 bucket name for storage
      OPENSEARCH_DOMAIN: props.openSearchCollection.attrCollectionEndpoint, // OpenSearch domain host
      TEMP_OPENSEARCH_DOMAIN:
        props.tempOpenSearchCollection.attrCollectionEndpoint, // Temporary OpenSearch domain host
      SM_ENDPOINT_NAME_SSM_PARAMETER:
        props.sagemakerEndpointNameSsmParameter.parameterName, // SSM parameter name for SageMaker endpoint
      VECTOR_INDEX_NAME: "img-vector", // Vector index name
      TEMP_VECTOR_INDEX_NAME: "img-vector", // Temporary vector index name
      COGNITO_REDIRECT_URL: `https://${props.userPoolDomain.domainName}/oauth2/idpresponse`, // Cognito redirect URL
      COGNITO_DOMAIN: `https://${props.userPoolDomain.domainName}.auth.ap-southeast-2.amazoncognito.com`, // Cognito domain URL
      HF_HOME: "/tmp", // Hugging Face home directory
      TRANSFORMERS_CACHE: "/tmp", // Transformers cache directory
      XDG_CACHE_HOME: "/tmp", // XDG cache home directory
      HUGGINGFACE_HUB_CACHE: "/tmp", // Hugging Face hub cache directory
    };

    this.handler = new DockerImageFunction(this, "Handler", {
      vpc: props.vpc,
      code: DockerImageCode.fromImageAsset(path.join(__dirname, "../../app"), {
        platform: Platform.LINUX_ARM64,
        file: "api.dockerfile",
      }),
      architecture: Architecture.ARM_64,
      memorySize: 10240,
      timeout: Duration.minutes(1),
      environment: this.fn_env_vars,
      role: handlerRole,
    });

    this.api = new LambdaRestApi(this, `${id}-rest-api`, {
      defaultCorsPreflightOptions: {
        allowOrigins: ["*"],
        allowMethods: ["GET", "PUT", "POST", "DELETE", "OPTIONS"],
      },
      defaultMethodOptions: {
        authorizationType: AuthorizationType.IAM,
      },
      handler: this.handler,
      proxy: true,
      policy: new iam.PolicyDocument({
        statements: [
          new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            principals: [
              new iam.AccountPrincipal(Stack.of(this).account),
              new iam.ArnPrincipal(props.ecsAppRole.roleArn), // Add ECS task role explicitly
            ],
            actions: ["execute-api:Invoke"],
            resources: ["execute-api:/*"],
          }),
          new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            principals: [new iam.AnyPrincipal()],
            actions: ["execute-api:Invoke"],
            resources: ["execute-api:/*/OPTIONS/*"],
          }),
        ],
      }),
    });

    // This workaround needed to avoid CORS preflight requests being blocked by the authorizer
    this.api.methods
      .filter((method) => method.httpMethod === "OPTIONS")
      .forEach((method) => {
        const methodCfn = method.node.defaultChild as CfnMethod;
        methodCfn.authorizationType = AuthorizationType.NONE;
        methodCfn.authorizerId = undefined;
      });

    new CfnOutput(this, "FraudDetectionApiUrl", { value: this.api.url });
  }
}
