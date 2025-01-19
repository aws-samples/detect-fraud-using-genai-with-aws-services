import { Stack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";
import { NetworkConstruct } from "../resources/Network";
import { StorageConstruct } from "../resources/Storage";
import { AuthConstruct } from "../resources/Auth";
import { AppFargateConstruct } from "../resources/App";
import { ParametersConstruct } from "../resources/Parameters";
import { DatabaseConstruct } from "../resources/Database";
import { SearchConstruct } from "../resources/Search";
import { FraudDetectionApi } from "../resources/Api";
import { LocationConstruct } from "../resources/Location";

// import * as sqs from 'aws-cdk-lib/aws-sqs';

export class InfraStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // The code that defines your stack goes here

    new LocationConstruct(this, "Location");

    const { vpc } = new NetworkConstruct(this, "network", {});

    const { StorageBucket, LogsBucket } = new StorageConstruct(this, "storage");

    const database = new DatabaseConstruct(this, "database");

    const { SerpApiKeySecret, SagemakerEndpointNameSsmParameter } =
      new ParametersConstruct(this, "parameters");

    const {
      identityPool,
      ecsAppRole,
      ecsRole,
      userPoolClient,
      userPoolDomain,
      userPool,
    } = new AuthConstruct(this, "auth", { storageBucket: StorageBucket });

    const search = new SearchConstruct(this, "search", {
      vpc,
      ecsRole,
    });

    const env_vars = {
      vpc,
      indexedFilesTable: database.IndexedFileTable,
      identityPool,
      ecsAppRole,
      sagemakerEndpointNameSsmParameter: SagemakerEndpointNameSsmParameter,
      openSearchCollection: search.opensearchCollection,
      SerpApiKeySecret: SerpApiKeySecret,
      userPool,
      indexedFileTable: database.IndexedFileTable,
      userPoolDomain,
      storageBucket: StorageBucket,
      userPoolClient,
      ecsRole,
      logsBucket: LogsBucket,
      tempOpenSearchCollection: search.tempOpenSearchCollection,
    };

    const api = new FraudDetectionApi(this, "api", env_vars);

    new AppFargateConstruct(this, "appEcs", {
      ...env_vars,
      api: api.api,
    });
  }
}
