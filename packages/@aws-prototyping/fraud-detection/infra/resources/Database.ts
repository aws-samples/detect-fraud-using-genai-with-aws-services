import { Construct } from "constructs";
import {
  AttributeType,
  BillingMode,
  Table,
  TableEncryption,
} from "aws-cdk-lib/aws-dynamodb";
import { RemovalPolicy } from "aws-cdk-lib";

export class DatabaseConstruct extends Construct {
  readonly IndexedFileTable: Table;

  constructor(scope: Construct, id: string) {
    super(scope, id);
    this.IndexedFileTable = new Table(this, `${id}-IndexFiles`, {
      partitionKey: { name: "id", type: AttributeType.STRING },
      encryption: TableEncryption.AWS_MANAGED,
      removalPolicy: RemovalPolicy.DESTROY,
      billingMode: BillingMode.PAY_PER_REQUEST,
    });
  }
}
