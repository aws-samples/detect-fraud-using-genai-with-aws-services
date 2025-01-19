import { Construct } from "constructs";
import { Secret } from "aws-cdk-lib/aws-secretsmanager";
import { CfnOutput, SecretValue } from "aws-cdk-lib";
import { SERP_API_KEY } from "../env";
import { StringParameter } from "aws-cdk-lib/aws-ssm";

export class ParametersConstruct extends Construct {
  readonly SerpApiKeySecret: Secret;
  readonly SagemakerEndpointNameSsmParameter: StringParameter;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    this.SerpApiKeySecret = new Secret(this, "SERPApiKeySecret", {
      secretName: "SERPApiKeySecret", 
      secretStringValue: SecretValue.unsafePlainText(SERP_API_KEY),
      description: "API key for a SERP service",
    });

    new CfnOutput(this, "SERPApiKeySecretArn", {
      value: this.SerpApiKeySecret.secretArn,
      description: "ARN of the SERP API Key Secret",
      exportName: "SERPApiKeySecretArn"
    });

    this.SagemakerEndpointNameSsmParameter = new StringParameter(
      this,
      "SagemakerEndpointNameSsmParameter",
      {
        parameterName: "/fraud-detection/sagemaker/endpoint/name",
        stringValue: "fraud-detection-sagemaker",
        description: "Sagemaker endpoint name for fraud detection",
      }
    );
  }
}
