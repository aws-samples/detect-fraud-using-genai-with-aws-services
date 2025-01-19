import { Construct } from "constructs";
import {
  Peer,
  Port,
  SecurityGroup,
  SubnetType,
  Vpc,
} from "aws-cdk-lib/aws-ec2";
import * as opensearchserverless from "aws-cdk-lib/aws-opensearchserverless";
import { Stack } from "aws-cdk-lib";
import { Role } from "aws-cdk-lib/aws-iam";

export interface SearchConstructProps {
  vpc: Vpc;
  ecsRole: Role;
}

export class SearchConstruct extends Construct {
  readonly opensearchCollection: opensearchserverless.CfnCollection;
  // The temp open search collection is used for emphemeral searches (e.g. internet reverse search)
  readonly tempOpenSearchCollection: opensearchserverless.CfnCollection;

  constructor(scope: Construct, id: string, props: SearchConstructProps) {
    super(scope, id);

    this.opensearchCollection = this.createCollection(
      id,
      "fd-col",
      props.ecsRole
    );
    this.tempOpenSearchCollection = this.createCollection(
      id,
      "fd-temp-col",
      props.ecsRole
    );
  }

  createCollection = (id: string, collectionName: string, ecsRole: Role) => {
    const networkSecurityPolicy = new opensearchserverless.CfnSecurityPolicy(
      this,
      `${collectionName}aossNetworkSecPolicy`,
      {
        policy: JSON.stringify([
          {
            Rules: [
              {
                Resource: [`collection/${collectionName}`],
                ResourceType: "dashboard",
              },
              {
                Resource: [`collection/${collectionName}`],
                ResourceType: "collection",
              },
            ],
            AllowFromPublic: true,
          },
        ]),
        name: `${collectionName}-sec-policy`,
        type: "network",
      }
    );

    const encryptionSecPolicy = new opensearchserverless.CfnSecurityPolicy(
      this,
      `${collectionName}aossEncryptionSecPolicy`,
      {
        name: `${collectionName}-enc-sec-pol`,
        type: "encryption",
        policy: JSON.stringify({
          Rules: [
            {
              Resource: [`collection/${collectionName}`],
              ResourceType: "collection",
            },
          ],
          AWSOwnedKey: true,
        }),
      }
    );

    // Create the OpenSearch Serverless collection
    const collection = new opensearchserverless.CfnCollection(
      this,
      `${id}${collectionName}}Collection`,
      {
        name: collectionName,
        description:
          "Collection to be used for vector search using OpenSearch Serverless",
        type: "VECTORSEARCH",
      }
    );

    collection.addDependency(networkSecurityPolicy);
    collection.addDependency(encryptionSecPolicy);

    new opensearchserverless.CfnAccessPolicy(
      this,
      `${collectionName}dataAccessPolicy`,
      {
        name: `${collectionName}-dap`,
        description: `Data access policy for: ${collectionName}`,
        type: "data",
        policy: JSON.stringify([
          {
            Rules: [
              {
                Resource: [`collection/${collectionName}`],
                Permission: [
                  "aoss:CreateCollectionItems",
                  "aoss:DeleteCollectionItems",
                  "aoss:UpdateCollectionItems",
                  "aoss:DescribeCollectionItems",
                ],
                ResourceType: "collection",
              },
              {
                Resource: [`index/${collectionName}/*`],
                Permission: [
                  "aoss:CreateIndex",
                  "aoss:DeleteIndex",
                  "aoss:UpdateIndex",
                  "aoss:DescribeIndex",
                  "aoss:ReadDocument",
                  "aoss:WriteDocument",
                ],
                ResourceType: "index",
              },
            ],
            Principal: [
              `arn:aws:iam::${Stack.of(this).account}:role/${ecsRole.roleName}`,
              `arn:aws:iam::${Stack.of(this).account}:role/Admin`,
            ],
            Description: "data-access-rule",
          },
        ]),
      }
    );

    return collection;
  };
}
