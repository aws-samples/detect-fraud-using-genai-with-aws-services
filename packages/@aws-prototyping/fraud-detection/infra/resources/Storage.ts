import * as s3 from "aws-cdk-lib/aws-s3";
import {BlockPublicAccess, Bucket, BucketEncryption, ObjectOwnership} from "aws-cdk-lib/aws-s3";
import {Construct} from "constructs";
import {RemovalPolicy} from "aws-cdk-lib";


export class StorageConstruct extends Construct {
    public readonly StorageBucket: Bucket;
    public readonly LogsBucket: Bucket

    constructor(scope: Construct, id: string) {
        super(scope, id);


        this.LogsBucket = new Bucket(this, `${id}-logs-bucket`, {
            encryption: BucketEncryption.S3_MANAGED,
            enforceSSL: true,
            objectOwnership: ObjectOwnership.OBJECT_WRITER,
            publicReadAccess: false,
            blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
            versioned: false,
            removalPolicy: RemovalPolicy.DESTROY
        });

        this.StorageBucket = new Bucket(this, `${id}-storage-bucket`, {
            encryption: BucketEncryption.S3_MANAGED,
            enforceSSL: true,
            publicReadAccess: false,
            blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
            serverAccessLogsBucket: this.LogsBucket,
            serverAccessLogsPrefix: 'storage-bucket-logs',
            objectOwnership: ObjectOwnership.OBJECT_WRITER,
            versioned: false,
            removalPolicy: RemovalPolicy.DESTROY,
            cors: [
                {
                    allowedMethods: [
                        s3.HttpMethods.GET,
                    ],
                    allowedOrigins: ["*"],
                    allowedHeaders: [],
                }
            ]
        });
    }
}
