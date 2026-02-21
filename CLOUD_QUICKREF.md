# Cloud Provider Quick Reference

## 🚀 30-Second Setup

### AWS
```bash
cd aws
aws cloudformation create-stack --stack-name doc-archive --template-body file://s3_bucket.yaml --capabilities CAPABILITY_NAMED_IAM
```

### Azure
```bash
cd azure
az deployment group create --resource-group doc-archive-rg --template-file blob_storage.bicep
```

### GCP
```bash
cd gcp
terraform init && terraform apply -var="project_id=my-project"
```

---

## 📊 Quick Comparison

| Aspect | AWS | Azure | GCP |
|--------|-----|-------|-----|
| **Speed** | ⚡⚡⚡ Fast | ⚡⚡ Medium | ⚡⚡⚡ Fast |
| **Cost** | $$$ | $$ | $ |
| **Archive Tier** | Glacier | Archive | Archive |
| **Deep Archive** | Yes | No | Via Archive |
| **IaC Tool** | CloudFormation | Bicep | Terraform |
| **Ease** | Medium | Easy | Medium |
| **Features** | Most | Good | Good |

---

## 💰 Monthly Cost (1TB)

```
HOT:     AWS $23  | Azure $18  | GCP $20
COOL:    AWS $12  | Azure $11  | GCP $10
ARCHIVE: AWS $4   | Azure $3   | GCP $4
DEEP:    AWS $2   | Azure --   | GCP $1
MIXED:   AWS $7   | Azure $6   | GCP $5    ← Typical
```

**GCP wins on price. AWS wins on features. Azure wins on integration.**

---

## 🔑 Key Credentials

### AWS
- Access Key ID
- Secret Access Key
- Region (default: us-east-1)

### Azure
- Resource Group
- Storage Account Key (or use Managed Identity)
- Region (default: eastus)

### GCP
- Project ID
- Service Account JSON (or Application Default)
- Region (default: us-central1)

---

## 📁 Where Everything Is

```
aws/           → s3_bucket.yaml + README.md
azure/         → blob_storage.bicep + README.md
gcp/           → gcs_bucket.tf + README.md
```

Each has complete setup guide + examples.

---

## 📋 Post-Deployment Steps

1. Get bucket/container name from deployment output
2. Get IAM credentials
3. Update `config.yaml`:
   ```yaml
   storage:
     provider: aws_s3  # or azure_blob or gcp_storage
   ```
4. Start app:
   ```bash
   python -m app.main
   ```

---

## 🔗 Useful Links

- [AWS S3 Pricing](https://aws.amazon.com/s3/pricing/)
- [Azure Storage Pricing](https://azure.microsoft.com/pricing/details/storage/)
- [GCP Storage Pricing](https://cloud.google.com/storage/pricing)
- [CLOUD_PROVIDERS.md](CLOUD_PROVIDERS.md) - Full comparison
- [cloud-deploy.sh](cloud-deploy.sh) - Automated deployment

---

## ⚡ Pro Tips

1. **Multi-cloud**: Deploy all three, use `database.url: iceberg` for provider-agnostic metadata
2. **Cost saving**: Enable lifecycle policies to 365+ days in archive
3. **Security**: Use managed identity (Azure) or service account (GCP), not API keys
4. **Backup**: Always enable versioning
5. **Monitoring**: Enable CloudTrail (AWS), Activity Log (Azure), Cloud Audit (GCP)

---

## 🆘 Troubleshooting

### Can't connect to S3/Blob/GCS?
- Check credentials
- Check region/project
- Check IAM permissions
- Check bucket name

### Too expensive?
- Enable lifecycle policies
- Move old data to archive tier
- Reduce retention period

### Deployment failed?
- Check template syntax (see README in that folder)
- Verify credentials
- Check quotas/limits

---

## 📞 Help

- AWS: `aws cloudformation describe-stacks --stack-name doc-archive`
- Azure: `az deployment group show --resource-group doc-archive-rg`
- GCP: `terraform show` (from gcp folder)

---

**Pick one. Deploy. Done. 🎉**
