import * as cdk from "aws-cdk-lib";
import { CfnOutput, Duration, RemovalPolicy, Stage } from "aws-cdk-lib";
import {
  AdvancedSecurityMode,
  CfnIdentityPool,
  CfnIdentityPoolRoleAttachment,
  StringAttribute,
  UserPool,
  UserPoolClient,
  UserPoolDomain,
  VerificationEmailStyle,
} from "aws-cdk-lib/aws-cognito";
import {
  Effect,
  FederatedPrincipal,
  Policy,
  PolicyDocument,
  PolicyStatement,
  Role,
  ServicePrincipal,
} from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";
import { Bucket } from "aws-cdk-lib/aws-s3";

export interface AuthConstructProps {
  readonly storageBucket: Bucket;
}

export class AuthConstruct extends Construct {
  public readonly userPool: UserPool;
  public readonly userPoolClient: UserPoolClient;
  public readonly userPoolDomain: UserPoolDomain;
  public readonly identityPool: CfnIdentityPool;
  public readonly authenticatedRole: Role;
  public readonly unauthenticatedRole: Role;
  public readonly identityPoolRoleAttachment: CfnIdentityPoolRoleAttachment;
  public readonly groundTruthRole: Role;
  public readonly ecsRole: Role;
  public readonly ecsAppRole: Role;

  constructor(scope: Construct, id: string, props: AuthConstructProps) {
    super(scope, id);

    const stageName = Stage.of(this)?.stageName;

    this.userPool = new UserPool(this, `${id}userpool`, {
      selfSignUpEnabled: false,
      signInAliases: {
        email: true,
      },
      autoVerify: {
        email: true,
      },
      userVerification: {
        emailSubject: "You need to verify your email",
        emailBody:
          "Thanks for signing up for the Insurance Claim Image Fraud Detection Solution. Click to verify your account: {##Verify Email##}", // # This placeholder is a must if code is selected as preferred verification method
        emailStyle: VerificationEmailStyle.LINK,
      },
      passwordPolicy: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
        tempPasswordValidity: Duration.days(3),
      },
      advancedSecurityMode: AdvancedSecurityMode.ENFORCED,
      customAttributes: {
        uiTheme: new StringAttribute({ mutable: true }),
        uiDensity: new StringAttribute({ mutable: true }),
      },
      deletionProtection: false,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    this.userPoolDomain = this.userPool.addDomain(`userpooldomain`, {
      cognitoDomain: {
        domainPrefix:
          `${stageName}frauddetection`.toLowerCase() +
          cdk.Stack.of(this).account +
          "-" +
          cdk.Stack.of(this).region,
      },
    });

    this.userPoolClient = this.userPool.addClient(`${id}userpoolclient`, {
      authFlows: {
        userPassword: true,
        userSrp: true,
      },
      generateSecret: true,
      // oAuth: { callbackUrls: clientURLs, logoutUrls: clientURLs },
    });

    this.identityPool = new CfnIdentityPool(this, `IdentityPool`, {
      allowUnauthenticatedIdentities: false,
      cognitoIdentityProviders: [
        {
          clientId: this.userPoolClient.userPoolClientId,
          providerName: this.userPool.userPoolProviderName,
        },
      ],
    });

    // Role associated with unauthenticated users
    this.unauthenticatedRole = new Role(this, `UnauthenticatedRole`, {
      assumedBy: new FederatedPrincipal(
        "cognito-identity.amazonaws.com",
        {
          StringEquals: {
            "cognito-identity.amazonaws.com:aud": this.identityPool.ref,
          },
          "ForAnyValue:StringLike": {
            "cognito-identity.amazonaws.com:amr": "unauthenticated",
          },
        },
        "sts:AssumeRoleWithWebIdentity"
      ),
    });

    // Role associated with authenticated users
    this.authenticatedRole = new Role(this, `AuthenticatedRole`, {
      assumedBy: new FederatedPrincipal(
        "cognito-identity.amazonaws.com",
        {
          StringEquals: {
            "cognito-identity.amazonaws.com:aud": this.identityPool.ref,
          },
          "ForAnyValue:StringLike": {
            "cognito-identity.amazonaws.com:amr": "authenticated",
          },
        },
        "sts:AssumeRoleWithWebIdentity"
      ),
    });

    // Attach the unauthenticated and authenticated roles to the identity pool
    this.identityPoolRoleAttachment = new CfnIdentityPoolRoleAttachment(
      this,
      `RoleAttachment`,
      {
        identityPoolId: this.identityPool.ref,
        roles: {
          unauthenticated: this.unauthenticatedRole.roleArn,
          authenticated: this.authenticatedRole.roleArn,
        },
      }
    );

    this.groundTruthRole = new Role(this, "GroundTruthRole", {
      assumedBy: new ServicePrincipal("sagemaker.amazonaws.com"),
    });

    const groundTruthDocument = new PolicyDocument({
      statements: [
        // Allow SageMaker Ground Truth to perform labeling jobs
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: [
            "sagemaker:CreateLabelingJob",
            "sagemaker:DescribeLabelingJob",
            "sagemaker:ListLabelingJobsForWorkteam",
            "sagemaker:ListWorkteams",
            "sagemaker:StopLabelingJob",
            "sagemaker:CreateWorkteam",
            "sagemaker:DeleteWorkteam",
            "sagemaker:UpdateWorkteam",
            "sagemaker:ListUserProfiles",
          ],
          resources: ["*"], // Replace with specific resources if necessary
        }),
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: ["lambda:InvokeFunction"],
          resources: [
            "arn:aws:lambda:ap-southeast-2:454466003867:function:PRE-BoundingBox",
          ],
        }),
      ],
    });

    const groundTruthPolicy = new Policy(this, "ground-truth-policy", {
      document: groundTruthDocument,
    });

    this.groundTruthRole.attachInlinePolicy(groundTruthPolicy);

    props.storageBucket.grantReadWrite(this.groundTruthRole);

    // Create an inline policy document to replicate the AmazonECSTaskExecutionRolePolicy
    const ecsPolicyDoc = new PolicyDocument({
      statements: [
        // Allow ECS tasks to pull images from ECR
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: [
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage",
            "ecr:BatchCheckLayerAvailability",
          ],
          resources: ["*"],
        }),
        // Allow ECS tasks to send logs to CloudWatch
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: [
            "logs:CreateLogStream",
            "logs:PutLogEvents",
            "logs:CreateLogGroup",
          ],
          resources: ["arn:aws:logs:*:*:log-group:/ecs/*"],
        }),
        // Allow ECS tasks to describe the EC2 instances in the cluster
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: ["ec2:Describe*", "rekognition:*", "sagemaker:*"],
          resources: ["*"],
        }),
        // Allow ECS tasks to access the Task Metadata Endpoint
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: [
            "ecs:CreateCluster",
            "ecs:DeregisterContainerInstance",
            "ecs:DiscoverPollEndpoint",
            "ecs:Poll",
            "ecs:RegisterContainerInstance",
            "ecs:StartTelemetrySession",
            "ecs:Submit*",
            "ecs:StartTask",
            "ecs:StopTask",
            "ecs:UpdateContainerInstancesState",
            "ecs:UpdateService",
            "rekognition:DetectLabels",
            "sagemaker:*",
          ],
          resources: ["*"],
        }),
        // Allow ECS tasks to create and delete temporary files
        new PolicyStatement({
          effect: Effect.ALLOW,
          actions: [
            "s3:CreateBucket",
            "s3:DeleteBucket",
            "s3:DeleteObject",
            "s3:GetBucketLocation",
            "s3:GetObject",
            "s3:ListBucket",
            "s3:PutObject",
          ],
          resources: ["arn:aws:s3:::codepipeline-*"],
        }),
      ],
    });

    this.ecsRole = new Role(this, `${id}EcsExecutionRole`, {
      assumedBy: new ServicePrincipal("ecs-tasks.amazonaws.com"),
    });

    const ecsRolePolicy = new Policy(this, `${id}-ecs-policy`, {
      document: ecsPolicyDoc,
    });

    this.ecsRole.attachInlinePolicy(ecsRolePolicy);

    this.ecsAppRole = new Role(this, `${id}app-role`, {
      assumedBy: new ServicePrincipal("ecs-tasks.amazonaws.com"),
    });

    props.storageBucket.grantReadWrite(this.ecsRole);

    new CfnOutput(this, "userPoolId", {
      value: this.userPool.userPoolId,
    });

    new CfnOutput(this, "userPoolClientId", {
      value: this.userPoolClient.userPoolClientId,
    });
  }
}
