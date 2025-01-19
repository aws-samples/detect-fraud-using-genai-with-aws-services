import * as cdk from "aws-cdk-lib";
import * as location from "aws-cdk-lib/aws-location";
import { Construct } from "constructs";

export class LocationConstruct extends Construct {
  /**
   * The Place Index reference
   */
  public readonly placeIndex: location.CfnPlaceIndex;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    // Create a Place Index with Esri as the data provider
    this.placeIndex = new location.CfnPlaceIndex(this, "PlaceIndex", {
      dataSource: "Esri", // Using Esri as the data provider
      indexName: "claims-index",
      pricingPlan: "RequestBasedUsage", // Pay per request
      dataSourceConfiguration: {
        // Configure the data source to include address and position search
        intendedUse: "SingleUse",
      },
      description: "Place index for geocoding and reverse geocoding",
    });
  }
}
