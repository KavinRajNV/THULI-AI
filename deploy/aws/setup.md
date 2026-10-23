# 🚀 AWS ECS Fargate Deployment Guide (PowerShell)

This guide provides end-to-end, copy-paste **PowerShell** commands for provisioning the Thuli AI backend on **Amazon ECS Fargate** using minimal, low-cost AWS resources (0.25 vCPU, 0.5 GB RAM, single public subnet, no NAT gateway).

> [!IMPORTANT]
> All commands use PowerShell syntax (`$VARIABLE = "..."`). Replace placeholder values enclosed in `<...>` with your desired configuration before running.

---

## 0. Prerequisites & Setup Session Variables

Open PowerShell on Windows and set your deployment parameters:

```powershell
# 1. Verify AWS CLI v2 and Docker Desktop are running
aws --version
docker --version

# 2. Configure session variables (replace placeholders as needed)
$AWS_REGION               = "ap-south-1"                  # Mumbai region (closest to Tamil Nadu)
$APP_NAME                 = "thuli-ai"
$ECR_REPO_NAME            = "thuli-ai"
$S3_BUCKET_NAME           = "thuli-ai-models-<AWS_ACCOUNT_ID>"  # S3 bucket names must be globally unique
$SECRET_NAME              = "thuli-ai/production"
$ECS_CLUSTER_NAME         = "thuli-ai-cluster"
$ECS_SERVICE_NAME         = "thuli-ai-service"
$EXECUTION_ROLE_NAME      = "ThuliAI-ECSTaskExecutionRole"
$TASK_ROLE_NAME           = "ThuliAI-ECSTaskRole"
$GITHUB_DEPLOY_ROLE_NAME  = "ThuliAI-GitHubDeployRole"
$GITHUB_ORG               = "<GITHUB_ORG>"                # e.g., "KavinRajNV"
$GITHUB_REPO              = "<GITHUB_REPO>"               # e.g., "KISAN-AI"

# 3. Retrieve your AWS Account ID automatically
$AWS_ACCOUNT_ID = (aws sts get-caller-identity --query "Account" --output text)
Write-Host "Connected to AWS Account ID: $AWS_ACCOUNT_ID in region: $AWS_REGION"
```

---

## 1. Create Amazon ECR Repository

Create the container repository to store the multi-stage Docker image:

```powershell
aws ecr create-repository `
  --repository-name $ECR_REPO_NAME `
  --region $AWS_REGION `
  --image-scanning-configuration scanOnPush=true `
  --encryption-configuration encryptionType=AES256

$ECR_REGISTRY = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
Write-Host "ECR Repository URI: $ECR_REGISTRY/$ECR_REPO_NAME"
```

---

## 2. Create Amazon S3 Bucket (Private, Versioned, Encrypted)

Create a dedicated S3 bucket to store large ML model weights and optional call recordings:

```powershell
# Create bucket (LocationConstraint required outside us-east-1)
if ($AWS_REGION -eq "us-east-1") {
    aws s3api create-bucket --bucket $S3_BUCKET_NAME --region $AWS_REGION
} else {
    aws s3api create-bucket `
      --bucket $S3_BUCKET_NAME `
      --region $AWS_REGION `
      --create-bucket-configuration LocationConstraint=$AWS_REGION
}

# Block all public access
aws s3api put-public-access-block `
  --bucket $S3_BUCKET_NAME `
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Enable S3 bucket versioning
aws s3api put-bucket-versioning `
  --bucket $S3_BUCKET_NAME `
  --versioning-configuration Status=Enabled

# Enable default server-side encryption (AES256)
aws s3api put-bucket-encryption `
  --bucket $S3_BUCKET_NAME `
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

Write-Host "✅ S3 Bucket created: s3://$S3_BUCKET_NAME"
```

---

## 3. Upload ML Model Artifacts & Datasets to S3

Upload model artifacts from your local disk into `s3://$S3_BUCKET_NAME/models/`:

```powershell
# Upload crop recommendation & reservoir models
if (Test-Path "backend/Dataset/RandomForest.pkl") {
    aws s3 cp "backend/Dataset/RandomForest.pkl" "s3://$S3_BUCKET_NAME/models/RandomForest.pkl"
}

if (Test-Path "backend/models/crop recommendation/XGBoost.pkl") {
    aws s3 cp "backend/models/crop recommendation/XGBoost.pkl" "s3://$S3_BUCKET_NAME/models/XGBoost.pkl"
}

# Upload fine-tuned IndicBERT intent model weights (~1.1 GB)
if (Test-Path "backend/models/intent_model") {
    aws s3 sync "backend/models/intent_model" "s3://$S3_BUCKET_NAME/models/intent_model"
}

# Upload FAISS vector indices & Knowledge Base
if (Test-Path "backend/data/faiss_indices") {
    aws s3 sync "backend/data/faiss_indices" "s3://$S3_BUCKET_NAME/models/faiss_indices"
}
if (Test-Path "backend/data/kb_data_gen.json") {
    aws s3 cp "backend/data/kb_data_gen.json" "s3://$S3_BUCKET_NAME/models/kb_data_gen.json"
}

# Upload core datasets (Villages, Soil data, etc.)
if (Test-Path "backend/Dataset") {
    aws s3 sync "backend/Dataset" "s3://$S3_BUCKET_NAME/models/Dataset" --exclude "*.pkl" --exclude "*.safetensors"
}

# Verify S3 objects
aws s3 ls "s3://$S3_BUCKET_NAME/models/" --recursive --human-readable
```

---

## 4. Store Secrets in AWS Secrets Manager

Store API keys and database credentials securely. **Never commit these values to Git!**

```powershell
# Create JSON payload with your credentials
$SecretsPayload = @{
    SARVAM_API_KEY        = "<YOUR_SARVAM_API_KEY>"
    GROQ_API_KEY          = "<YOUR_GROQ_API_KEY>"
    DATABASE_URL          = "<YOUR_POSTGRES_ASYNC_URL>"   # postgresql+asyncpg://user:pass@host:5432/thuli_ai
    DATABASE_URL_SYNC     = "<YOUR_POSTGRES_SYNC_URL>"    # postgresql://user:pass@host:5432/thuli_ai
    EXOTEL_API_KEY        = "<YOUR_EXOTEL_API_KEY>"
    EXOTEL_API_TOKEN      = "<YOUR_EXOTEL_API_TOKEN>"
    EXOTEL_SID            = "<YOUR_EXOTEL_SID>"
    EXOTEL_VIRTUAL_NUMBER = "<YOUR_EXOTEL_VIRTUAL_NUMBER>"
    BASE_URL              = "https://<YOUR_DOMAIN_OR_URL>"
    GEMINI_API_KEY        = "<YOUR_GEMINI_API_KEY>"
    OPENAI_API_KEY        = "<YOUR_OPENAI_API_KEY>"
    WEATHER_API_KEY       = "<YOUR_WEATHER_API_KEY>"
} | ConvertTo-Json -Compress

aws secretsmanager create-secret `
  --name $SECRET_NAME `
  --description "Production credentials for Thuli AI FastAPI backend" `
  --secret-string $SecretsPayload `
  --region $AWS_REGION

$SECRET_ARN = (aws secretsmanager describe-secret --secret-id $SECRET_NAME --query "ARN" --output text --region $AWS_REGION)
Write-Host "✅ Secrets Manager Secret ARN: $SECRET_ARN"
```

---

## 5. Create IAM Roles & Policies

### 5.1 ECS Task Execution Role (Pull image, read secrets, write logs)

```powershell
# 1. Create Task Execution Role
aws iam create-role `
  --role-name $EXECUTION_ROLE_NAME `
  --assume-role-policy-document file://deploy/aws/iam/ecs-task-execution-role-trust-policy.json

# 2. Render execution policy with placeholders replaced
$ExecPolicy = (Get-Content deploy/aws/iam/ecs-task-execution-role-policy.json -Raw) `
  -replace "<AWS_ACCOUNT_ID>", $AWS_ACCOUNT_ID `
  -replace "<AWS_REGION>", $AWS_REGION `
  -replace "<ECR_REPOSITORY_NAME>", $ECR_REPO_NAME `
  -replace "<ECS_SERVICE_NAME>", $ECS_SERVICE_NAME `
  -replace "<SECRET_NAME>", $SECRET_NAME `
  -replace "<APP_NAME>", $APP_NAME `
  -replace "<KMS_KEY_ID>", "*"

# 3. Attach inline policy
aws iam put-role-policy `
  --role-name $EXECUTION_ROLE_NAME `
  --policy-name "ThuliAI-ECSTaskExecutionPolicy" `
  --policy-document $ExecPolicy

$EXECUTION_ROLE_ARN = (aws iam get-role --role-name $EXECUTION_ROLE_NAME --query "Role.Arn" --output text)
Write-Host "✅ Execution Role ARN: $EXECUTION_ROLE_ARN"
```

### 5.2 ECS Task Role (S3 read models, S3 write audio, application logging)

```powershell
# 1. Create Task Role
aws iam create-role `
  --role-name $TASK_ROLE_NAME `
  --assume-role-policy-document file://deploy/aws/iam/ecs-task-role-trust-policy.json

# 2. Render task policy with placeholders replaced
$TaskPolicy = (Get-Content deploy/aws/iam/ecs-task-role-policy.json -Raw) `
  -replace "<AWS_ACCOUNT_ID>", $AWS_ACCOUNT_ID `
  -replace "<AWS_REGION>", $AWS_REGION `
  -replace "<S3_BUCKET_NAME>", $S3_BUCKET_NAME `
  -replace "<S3_MODEL_PREFIX>", "models/" `
  -replace "<S3_AUDIO_PREFIX>", "audio/calls/" `
  -replace "<ECS_SERVICE_NAME>", $ECS_SERVICE_NAME

# 3. Attach inline policy
aws iam put-role-policy `
  --role-name $TASK_ROLE_NAME `
  --policy-name "ThuliAI-ECSTaskPolicy" `
  --policy-document $TaskPolicy

$TASK_ROLE_ARN = (aws iam get-role --role-name $TASK_ROLE_NAME --query "Role.Arn" --output text)
Write-Host "✅ Task Role ARN: $TASK_ROLE_ARN"
```

---

## 6. Create GitHub OIDC Provider & GitHub Actions Deploy Role

Allows GitHub Actions to push images and deploy without any static AWS keys:

```powershell
# 1. Create OIDC Provider if not already present
$ExistingProvider = aws iam list-open-id-connect-providers --query "OpenIDConnectProviderList[?contains(Arn, 'token.actions.githubusercontent.com')].Arn" --output text
if (-not $ExistingProvider) {
    aws iam create-open-id-connect-provider `
      --url "https://token.actions.githubusercontent.com" `
      --client-id-list "sts.amazonaws.com" `
      --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" "1c58a3a8518e8759bf075b76b750d4f8d264fcd9"
    Write-Host "Created GitHub OIDC Provider in IAM."
}

# 2. Render OIDC trust policy for your repository
$OIDCTrust = (Get-Content deploy/aws/iam/github-oidc-trust-policy.json -Raw) `
  -replace "<AWS_ACCOUNT_ID>", $AWS_ACCOUNT_ID `
  -replace "<GITHUB_ORG>", $GITHUB_ORG `
  -replace "<GITHUB_REPO>", $GITHUB_REPO

# 3. Create the Deploy Role
aws iam create-role `
  --role-name $GITHUB_DEPLOY_ROLE_NAME `
  --assume-role-policy-document $OIDCTrust

# 4. Render and attach deploy policy
$DeployPolicy = (Get-Content deploy/aws/iam/github-deploy-role-policy.json -Raw) `
  -replace "<AWS_ACCOUNT_ID>", $AWS_ACCOUNT_ID `
  -replace "<AWS_REGION>", $AWS_REGION `
  -replace "<ECR_REPOSITORY_NAME>", $ECR_REPO_NAME `
  -replace "<ECS_EXECUTION_ROLE_NAME>", $EXECUTION_ROLE_NAME `
  -replace "<ECS_TASK_ROLE_NAME>", $TASK_ROLE_NAME

aws iam put-role-policy `
  --role-name $GITHUB_DEPLOY_ROLE_NAME `
  --policy-name "ThuliAI-GitHubDeployPolicy" `
  --policy-document $DeployPolicy

$GITHUB_ROLE_ARN = (aws iam get-role --role-name $GITHUB_DEPLOY_ROLE_NAME --query "Role.Arn" --output text)
Write-Host "✅ Add this Secret to GitHub (Settings -> Secrets -> Actions -> AWS_ROLE_TO_ASSUME):"
Write-Host $GITHUB_ROLE_ARN
```

---

## 7. Create CloudWatch Log Group & ECS Cluster

```powershell
# Create CloudWatch Log Group
aws logs create-log-group `
  --log-group-name "/ecs/$ECS_SERVICE_NAME" `
  --region $AWS_REGION

# Set log retention to 14 days (saves CloudWatch costs)
aws logs put-retention-policy `
  --log-group-name "/ecs/$ECS_SERVICE_NAME" `
  --retention-in-days 14 `
  --region $AWS_REGION

# Create ECS Fargate Cluster
aws ecs create-cluster `
  --cluster-name $ECS_CLUSTER_NAME `
  --capacity-providers FARGATE FARGATE_SPOT `
  --region $AWS_REGION

Write-Host "✅ ECS Cluster created: $ECS_CLUSTER_NAME"
```

---

## 8. Build Image & Register Task Definition

### 8.1 Build & Push Initial Container Image

```powershell
# Authenticate Docker with Amazon ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Build image locally with Docker Desktop
docker build -f backend/Dockerfile -t "$ECR_REGISTRY/$ECR_REPO_NAME:latest" .

# Push image to ECR
docker push "$ECR_REGISTRY/$ECR_REPO_NAME:latest"
```

### 8.2 Register Task Definition

```powershell
# Substitute placeholders in ecs-task-definition.json
$TaskDefJson = (Get-Content deploy/aws/ecs-task-definition.json -Raw) `
  -replace "<AWS_ACCOUNT_ID>", $AWS_ACCOUNT_ID `
  -replace "<AWS_REGION>", $AWS_REGION `
  -replace "<ECR_REPOSITORY_NAME>", $ECR_REPO_NAME `
  -replace "<ECS_SERVICE_NAME>", $ECS_SERVICE_NAME `
  -replace "<ECS_EXECUTION_ROLE_NAME>", $EXECUTION_ROLE_NAME `
  -replace "<ECS_TASK_ROLE_NAME>", $TASK_ROLE_NAME `
  -replace "<S3_BUCKET_NAME>", $S3_BUCKET_NAME `
  -replace "<SECRET_NAME>", $SECRET_NAME

# Save temporary file and register
$TaskDefJson | Set-Content "deploy/aws/task-def-final.json"

aws ecs register-task-definition `
  --cli-input-json file://deploy/aws/task-def-final.json `
  --region $AWS_REGION

Remove-Item "deploy/aws/task-def-final.json" -ErrorAction SilentlyContinue
Write-Host "✅ Task definition registered successfully."
```

---

## 9. Launch ECS Service in a Public Subnet

For lowest cost, we launch the task in the default VPC's public subnet with a public IP (no NAT Gateway needed, saving ~$32/month):

```powershell
# 1. Retrieve Default VPC ID
$VPC_ID = (aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $AWS_REGION)

# 2. Retrieve Public Subnet ID
$SUBNET_ID = (aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[0].SubnetId" --output text --region $AWS_REGION)

# 3. Create Security Group for FastAPI (port 8000)
$SG_ID = (aws ec2 create-security-group `
  --group-name "thuli-ai-fargate-sg" `
  --description "Security group for Thuli AI Fargate service" `
  --vpc-id $VPC_ID `
  --query "GroupId" `
  --output text `
  --region $AWS_REGION)

# Allow inbound traffic on port 8000
aws ec2 authorize-security-group-ingress `
  --group-id $SG_ID `
  --protocol tcp `
  --port 8000 `
  --cidr 0.0.0.0/0 `
  --region $AWS_REGION

Write-Host "VPC: $VPC_ID | Subnet: $SUBNET_ID | Security Group: $SG_ID"

# 4. Create the ECS Fargate Service
aws ecs create-service `
  --cluster $ECS_CLUSTER_NAME `
  --service-name $ECS_SERVICE_NAME `
  --task-definition "thuli-ai-backend" `
  --desired-count 1 `
  --launch-type FARGATE `
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" `
  --region $AWS_REGION

Write-Host "✅ ECS Service created! Checking status..."
aws ecs describe-services --cluster $ECS_CLUSTER_NAME --services $ECS_SERVICE_NAME --region $AWS_REGION --query "services[0].status"
```

---

## 10. Getting an HTTPS URL for Exotel Webhooks

Exotel requires a public HTTPS URL (e.g. `https://<YOUR_DOMAIN>/exotel/incoming`). 

### Cost & Option Comparison

| Option | Monthly Cost | Setup Complexity | Best For |
|---|---|---|---|
| **Cloudflare Tunnel (Recommended)** | **$0.00 / month** | Low (5 mins) | **Hackathons, demos, lowest cost** |
| **AWS Application Load Balancer (ALB)** | **~$16 - $22 / month** | Medium | Production enterprise AWS setups |
| **ngrok / Localtunnel** | $0 to $8 / month | Very Low | Quick local debugging only |
| **AWS API Gateway (HTTP API)** | ~$1.00 / 1M requests | High (requires VPC Link) | Serverless APIs |

---

### Option A (Recommended Cheapest): Cloudflare Tunnel ($0 / month)

1. Sign up for a free [Cloudflare](https://dash.cloudflare.com/) account and connect your domain (or a free domain from Cloudflare Registrar / Namecheap).
2. Go to **Zero Trust** -> **Networks** -> **Tunnels** -> **Create a Tunnel**.
3. Choose **Cloudflared connector** and configure the public hostname:
   - **Subdomain**: `api` (e.g. `api.yourdomain.com`)
   - **Service Type**: `HTTP`
   - **URL**: `<PUBLIC_IP_OF_FARGATE_TASK>:8000`
4. Cloudflare automatically provides a valid **HTTPS SSL/TLS certificate**, DDoS protection, and routes calls from Exotel to your Fargate container.
5. In Exotel dashboard, set:
   - Webhook URL: `https://api.yourdomain.com/exotel/incoming`
   - Callback URL: `https://api.yourdomain.com/exotel/process`

---

### Option B: AWS Application Load Balancer + ACM Certificate (~$18 / month)

If you require an AWS-native setup:

```powershell
# 1. Request an AWS Certificate Manager (ACM) SSL certificate
aws acm request-certificate `
  --domain-name "api.yourdomain.com" `
  --validation-method DNS `
  --region $AWS_REGION

# 2. Create Application Load Balancer in public subnets
$SUBNET_ID_2 = (aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[1].SubnetId" --output text --region $AWS_REGION)

$ALB_ARN = (aws elbv2 create-load-balancer `
  --name "thuli-ai-alb" `
  --subnets $SUBNET_ID $SUBNET_ID_2 `
  --security-groups $SG_ID `
  --query "LoadBalancers[0].LoadBalancerArn" `
  --output text `
  --region $AWS_REGION)

# 3. Create Target Group for port 8000 with healthcheck /health
$TG_ARN = (aws elbv2 create-target-group `
  --name "thuli-ai-tg" `
  --protocol HTTP `
  --port 8000 `
  --vpc-id $VPC_ID `
  --target-type ip `
  --health-check-path "/health" `
  --health-check-interval-seconds 30 `
  --query "TargetGroups[0].TargetGroupArn" `
  --output text `
  --region $AWS_REGION)

# 4. Create HTTPS Listener (requires ACM certificate ARN)
$CERT_ARN = "<YOUR_ACM_CERTIFICATE_ARN>"
aws elbv2 create-listener `
  --load-balancer-arn $ALB_ARN `
  --protocol HTTPS `
  --port 443 `
  --certificates CertificateArn=$CERT_ARN `
  --default-actions Type=forward,TargetGroupArn=$TG_ARN `
  --region $AWS_REGION
```

---

## 11. Teardown / Cleanup (Delete Everything to Stop Charges)

When testing is complete, run these commands in order to completely remove all resources and stop any AWS charges:

```powershell
Write-Host "🧹 Initiating complete teardown of Thuli AI AWS infrastructure..."

# 1. Delete ECS Service (set desired count to 0 first)
aws ecs update-service --cluster $ECS_CLUSTER_NAME --service $ECS_SERVICE_NAME --desired-count 0 --region $AWS_REGION
aws ecs delete-service --cluster $ECS_CLUSTER_NAME --service $ECS_SERVICE_NAME --force --region $AWS_REGION

# 2. Delete ECS Cluster
aws ecs delete-cluster --cluster $ECS_CLUSTER_NAME --region $AWS_REGION

# 3. Delete CloudWatch Log Group
aws logs delete-log-group --log-group-name "/ecs/$ECS_SERVICE_NAME" --region $AWS_REGION

# 4. Delete ECR Repository (and all images)
aws ecr delete-repository --repository-name $ECR_REPO_NAME --force --region $AWS_REGION

# 5. Empty and Delete S3 Bucket
aws s3 rm "s3://$S3_BUCKET_NAME" --recursive
aws s3api delete-bucket --bucket $S3_BUCKET_NAME --region $AWS_REGION

# 6. Delete Secrets Manager Secret
aws secretsmanager delete-secret --secret-id $SECRET_NAME --force-delete-without-recovery --region $AWS_REGION

# 7. Delete IAM Roles & Policies
aws iam delete-role-policy --role-name $EXECUTION_ROLE_NAME --policy-name "ThuliAI-ECSTaskExecutionPolicy"
aws iam delete-role --role-name $EXECUTION_ROLE_NAME

aws iam delete-role-policy --role-name $TASK_ROLE_NAME --policy-name "ThuliAI-ECSTaskPolicy"
aws iam delete-role --role-name $TASK_ROLE_NAME

aws iam delete-role-policy --role-name $GITHUB_DEPLOY_ROLE_NAME --policy-name "ThuliAI-GitHubDeployPolicy"
aws iam delete-role --role-name $GITHUB_DEPLOY_ROLE_NAME

# 8. Delete Security Group (after tasks have exited)
Start-Sleep -Seconds 30
aws ec2 delete-security-group --group-id $SG_ID --region $AWS_REGION

Write-Host "✅ All AWS resources have been successfully deleted. Zero charges active."
```
