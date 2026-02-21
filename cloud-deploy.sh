#!/usr/bin/env bash
# Deploy document archive infrastructure to AWS, Azure, or GCP

set -e

usage() {
    echo "Usage: $0 <provider> <action> [options]"
    echo ""
    echo "Providers: aws, azure, gcp"
    echo "Actions: deploy, destroy, validate, status"
    echo ""
    echo "Examples:"
    echo "  $0 aws deploy --environment dev --budget-alert 100"
    echo "  $0 azure deploy --resource-group doc-archive-rg"
    echo "  $0 gcp deploy --project my-project --region us-central1"
    echo ""
    exit 1
}

if [ $# -lt 2 ]; then
    usage
fi

PROVIDER=$1
ACTION=$2
shift 2

# AWS Deployment
deploy_aws() {
    ENVIRONMENT=${ENVIRONMENT:-dev}
    BUCKET_NAME=${BUCKET_NAME:-document-archive}
    REGION=${REGION:-us-east-1}
    ICEBERG=${ICEBERG:-no}
    
    echo "🚀 Deploying Document Archive to AWS..."
    echo "   Environment: $ENVIRONMENT"
    echo "   Bucket: $BUCKET_NAME"
    echo "   Region: $REGION"
    echo "   Iceberg: $ICEBERG"
    echo ""
    
    aws cloudformation create-stack \
        --stack-name "document-archive-$ENVIRONMENT" \
        --template-body "file://aws/s3_bucket.yaml" \
        --parameters \
            "ParameterKey=BucketName,ParameterValue=$BUCKET_NAME" \
            "ParameterKey=EnvironmentTag,ParameterValue=$ENVIRONMENT" \
            "ParameterKey=CreateIcebergWarehouse,ParameterValue=$ICEBERG" \
        --capabilities CAPABILITY_NAMED_IAM \
        --region "$REGION"
    
    echo "✓ Stack created. Waiting for completion..."
    aws cloudformation wait stack-create-complete \
        --stack-name "document-archive-$ENVIRONMENT" \
        --region "$REGION"
    
    echo "✓ Deployment complete!"
    echo ""
    echo "Outputs:"
    aws cloudformation describe-stacks \
        --stack-name "document-archive-$ENVIRONMENT" \
        --query 'Stacks[0].Outputs' \
        --region "$REGION"
}

# Azure Deployment
deploy_azure() {
    RESOURCE_GROUP=${RESOURCE_GROUP:-doc-archive-rg}
    ENVIRONMENT=${ENVIRONMENT:-dev}
    REGION=${REGION:-eastus}
    ICEBERG=${ICEBERG:-false}
    
    echo "🚀 Deploying Document Archive to Azure..."
    echo "   Resource Group: $RESOURCE_GROUP"
    echo "   Environment: $ENVIRONMENT"
    echo "   Region: $REGION"
    echo "   Iceberg: $ICEBERG"
    echo ""
    
    # Create resource group if it doesn't exist
    az group create \
        --name "$RESOURCE_GROUP" \
        --location "$REGION"
    
    # Deploy Bicep template
    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "azure/blob_storage.bicep" \
        --parameters \
            "environment=$ENVIRONMENT" \
            "createIcebergWarehouse=$ICEBERG"
    
    echo "✓ Deployment complete!"
    echo ""
    echo "Outputs:"
    az deployment group show \
        --resource-group "$RESOURCE_GROUP" \
        --name blob_storage \
        --query properties.outputs
}

# GCP Deployment
deploy_gcp() {
    PROJECT_ID=${PROJECT_ID:-}
    ENVIRONMENT=${ENVIRONMENT:-dev}
    REGION=${REGION:-us-central1}
    ICEBERG=${ICEBERG:-false}
    
    if [ -z "$PROJECT_ID" ]; then
        echo "Error: PROJECT_ID required for GCP"
        echo "Usage: PROJECT_ID=my-project $0 gcp deploy"
        exit 1
    fi
    
    echo "🚀 Deploying Document Archive to GCP..."
    echo "   Project: $PROJECT_ID"
    echo "   Environment: $ENVIRONMENT"
    echo "   Region: $REGION"
    echo "   Iceberg: $ICEBERG"
    echo ""
    
    cd gcp
    
    # Initialize Terraform (if not done)
    if [ ! -d ".terraform" ]; then
        terraform init \
            -backend-config="bucket=$PROJECT_ID-terraform-state" \
            -backend-config="prefix=document-archive/$ENVIRONMENT"
    fi
    
    # Plan
    terraform plan \
        -var="project_id=$PROJECT_ID" \
        -var="environment=$ENVIRONMENT" \
        -var="region=$REGION" \
        -var="create_iceberg_warehouse=$ICEBERG" \
        -out="tfplan"
    
    # Apply
    terraform apply "tfplan"
    
    echo "✓ Deployment complete!"
    echo ""
    echo "Outputs:"
    terraform output
    
    cd ..
}

# Destroy functions
destroy_aws() {
    ENVIRONMENT=${ENVIRONMENT:-dev}
    REGION=${REGION:-us-east-1}
    
    echo "⚠️  Destroying AWS CloudFormation stack..."
    read -p "Are you sure? (yes/no): " confirm
    [ "$confirm" = "yes" ] || exit 0
    
    aws cloudformation delete-stack \
        --stack-name "document-archive-$ENVIRONMENT" \
        --region "$REGION"
    
    echo "✓ Stack deletion initiated"
}

destroy_azure() {
    RESOURCE_GROUP=${RESOURCE_GROUP:-doc-archive-rg}
    
    echo "⚠️  Destroying Azure resources..."
    read -p "Are you sure? (yes/no): " confirm
    [ "$confirm" = "yes" ] || exit 0
    
    az group delete \
        --name "$RESOURCE_GROUP" \
        --yes
    
    echo "✓ Resource group deleted"
}

destroy_gcp() {
    PROJECT_ID=${PROJECT_ID:-}
    ENVIRONMENT=${ENVIRONMENT:-dev}
    
    if [ -z "$PROJECT_ID" ]; then
        echo "Error: PROJECT_ID required"
        exit 1
    fi
    
    echo "⚠️  Destroying GCP resources..."
    read -p "Are you sure? (yes/no): " confirm
    [ "$confirm" = "yes" ] || exit 0
    
    cd gcp
    terraform destroy \
        -var="project_id=$PROJECT_ID" \
        -var="environment=$ENVIRONMENT"
    cd ..
    
    echo "✓ Resources deleted"
}

# Validate functions
validate_aws() {
    echo "Validating AWS template..."
    aws cloudformation validate-template \
        --template-body "file://aws/s3_bucket.yaml"
    echo "✓ Template valid"
}

validate_azure() {
    echo "Validating Azure Bicep template..."
    az bicep build --file azure/blob_storage.bicep
    echo "✓ Template valid"
}

validate_gcp() {
    echo "Validating GCP Terraform..."
    cd gcp
    terraform fmt -check .
    terraform validate
    cd ..
    echo "✓ Template valid"
}

# Status functions
status_aws() {
    ENVIRONMENT=${ENVIRONMENT:-dev}
    REGION=${REGION:-us-east-1}
    
    echo "AWS Stack Status:"
    aws cloudformation describe-stacks \
        --stack-name "document-archive-$ENVIRONMENT" \
        --region "$REGION" \
        --query 'Stacks[0].[StackStatus,CreationTime]'
}

status_azure() {
    RESOURCE_GROUP=${RESOURCE_GROUP:-doc-archive-rg}
    
    echo "Azure Resource Group Status:"
    az group show \
        --name "$RESOURCE_GROUP" \
        --query '[name,location,managedBy]'
}

status_gcp() {
    PROJECT_ID=${PROJECT_ID:-}
    ENVIRONMENT=${ENVIRONMENT:-dev}
    
    if [ -z "$PROJECT_ID" ]; then
        echo "Error: PROJECT_ID required"
        exit 1
    fi
    
    echo "GCP Project Status:"
    gcloud projects describe "$PROJECT_ID"
}

# Main dispatch
case "$PROVIDER" in
    aws)
        case "$ACTION" in
            deploy) deploy_aws "$@" ;;
            destroy) destroy_aws "$@" ;;
            validate) validate_aws "$@" ;;
            status) status_aws "$@" ;;
            *) echo "Unknown action: $ACTION"; usage ;;
        esac
        ;;
    azure)
        case "$ACTION" in
            deploy) deploy_azure "$@" ;;
            destroy) destroy_azure "$@" ;;
            validate) validate_azure "$@" ;;
            status) status_azure "$@" ;;
            *) echo "Unknown action: $ACTION"; usage ;;
        esac
        ;;
    gcp)
        case "$ACTION" in
            deploy) deploy_gcp "$@" ;;
            destroy) destroy_gcp "$@" ;;
            validate) validate_gcp "$@" ;;
            status) status_gcp "$@" ;;
            *) echo "Unknown action: $ACTION"; usage ;;
        esac
        ;;
    *)
        echo "Unknown provider: $PROVIDER"
        usage
        ;;
esac
