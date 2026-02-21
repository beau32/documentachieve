# AWS Configuration for Document Archive

AWS storage provisioning for document archiving with S3, Glacier, and Iceberg support.

## Files

- **s3_bucket.yaml** - CloudFormation template for AWS infrastructure
  - S3 bucket with lifecycle policies
  - Glacier Deep Archive Vault
  - IAM roles and policies
  - Optional Iceberg warehouse bucket
  - SNS notifications

## Quick Start

```bash
# Deploy to AWS
aws cloudformation create-stack \
  --stack-name document-archive \
  --template-body file://aws/s3_bucket.yaml \
  --parameters ParameterKey=BucketName,ParameterValue=my-docs \
              ParameterKey=EnvironmentTag,ParameterValue=dev \
              ParameterKey=CreateIcebergWarehouse,ParameterValue=yes \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Check status
aws cloudformation describe-stacks --stack-name document-archive --region us-east-1

# Get outputs
aws cloudformation describe-stacks \
  --stack-name document-archive \
  --query 'Stacks[0].Outputs' \
  --region us-east-1
```

## Configuration

Update `config.yaml`:

```yaml
storage:
  provider: aws_s3
  aws:
    access_key_id: "YOUR_KEY"
    secret_access_key: "YOUR_SECRET"
    region: us-east-1
    bucket: my-docs-123456789-dev
    glacier:
      restore_days: 7
      restore_tier: Standard
```

## Architecture

```
S3 Bucket
├── Standard tier (0-30 days)
├── Standard-IA tier (30-90 days)
├── Glacier Instant Retrieval (90-365 days)
└── Glacier Deep Archive (365+ days)

Glacier Vault
└── Long-term retention with SNS notifications

Iceberg Warehouse (optional)
└── S3-based metadata storage with ACID transactions
```

## Lifecycle Policies

- Day 0-30: S3 Standard
- Day 30-90: S3 Standard-IA
- Day 90-365: Glacier Instant Retrieval
- Day 365+: Glacier Deep Archive

Costs decrease from $0.023/GB (Standard) to $0.004/GB (Deep Archive)

## References

- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [AWS Glacier Documentation](https://docs.aws.amazon.com/AmazonGlacier/)
- [CloudFormation Reference](https://docs.aws.amazon.com/cloudformation/)
