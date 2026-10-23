# ☁️ Thuli AI — AWS Deployment & Architecture Documentation

This document describes the cloud architecture, security posture, configuration parameters, and post-deployment verification evidence checklist for **Thuli AI** on **Amazon Web Services (AWS)**.

---

## 1. Architecture Overview

Thuli AI is deployed as a containerized serverless workload on **Amazon ECS Fargate** designed for high reliability, minimal operational overhead, and low cloud expenditure.

```
                    ┌───────────────────────────────────────────────┐
                    │               AWS Cloud (ap-south-1)          │
                    │                                               │
Farmer Phone        │   ┌────────────────────────────────────────┐  │
    │               │   │ Public Subnet (Default VPC)            │  │
    ▼               │   │                                        │  │
Exotel (IVR) ───────┼───┼─► AWS ALB / Cloudflare Tunnel          │  │
                    │   │        │                               │  │
                    │   │        ▼ (Port 8000)                   │  │
                    │   │   ┌──────────────────────────────┐     │  │
                    │   │   │ ECS Fargate Task             │     │  │
                    │   │   │ - FastAPI App (Non-Root)     │     │  │
                    │   │   │ - 0.25 vCPU / 0.5 GB RAM     │     │  │
                    │   │   └──────┬──────────────┬────────┘     │  │
                    │   └──────────┼──────────────┼──────────────┘  │
                    │              │              │                 │
                    │              ▼              ▼                 │
                    │     Amazon S3 Bucket    AWS Secrets Manager   │
                    │     - models/           - API Keys            │
                    │     - audio/calls/      - DB Connection URL   │
                    │              │                                │
                    │              ▼                                │
                    │     CloudWatch Logs                           │
                    │     /ecs/<ECS_SERVICE_NAME>                   │
                    └───────────────────────────────────────────────┘
```

### Component Breakdown

| Layer | Service | Configuration / Role |
|---|---|---|
| **Container Registry** | Amazon ECR | Private Docker repository with AES256 encryption and scan-on-push enabled. |
| **Container Orchestration** | Amazon ECS (Fargate) | Runs the FastAPI container in a public subnet with a public IP assigned (no NAT gateway charges). Sized at 0.25 vCPU (256 units) and 0.5 GB RAM (512 MiB). |
| **Object Storage** | Amazon S3 | Dedicated private bucket (`<S3_BUCKET_NAME>`) with public access blocked and versioning enabled.<br>• `models/`: Stores large ML model binaries (`RandomForest.pkl`, `XGBoost.pkl`, `intent_model/`, vector indices).<br>• `audio/calls/`: Stores farmer call audio recordings (WebM/MP3) when `S3_UPLOAD_AUDIO=true`. |
| **Secrets Management** | AWS Secrets Manager | Stores API keys (`SARVAM_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`, `WEATHER_API_KEY`, `EXOTEL_*`) and PostgreSQL database URLs. Secrets are injected at container startup using task definition `secrets.valueFrom`. |
| **Logging & Monitoring** | Amazon CloudWatch | Captures container stdout/stderr logs in `/ecs/<ECS_SERVICE_NAME>` with a 14-day retention policy. |
| **Continuous Deployment** | GitHub Actions (OIDC) | Secure keyless CI/CD. Authenticates via AWS IAM OpenID Connect (OIDC) provider, builds Docker image, pushes to ECR, and deploys to ECS. |
| **IVR & Audio Webhooks** | Exotel -> Webhook | Farmers dial into Exotel; webhooks are forwarded over HTTPS to `/exotel/incoming` and `/exotel/process`. |

---

## 2. Security & Compliance Posture

1. **Least Privilege IAM Roles**:
   - **Task Execution Role**: Limited to pulling from the specific ECR repository, creating CloudWatch log streams, and reading the designated secret in Secrets Manager.
   - **Task Role**: Limited to `s3:GetObject` on `models/*` and `s3:PutObject` on `audio/calls/*`.
   - **GitHub Deploy Role**: Scoped exclusively to the repository's `main` branch via OIDC `sub` claim.
2. **Non-Root Container Execution**: The Docker container runs under an unprivileged user `appuser` (UID `10001`), preventing container breakout vulnerabilities.
3. **Zero Secrets in Repository**: No API keys, credentials, or `.env` files are stored in Git. All secrets are retrieved dynamically via AWS Secrets Manager.
4. **Data Protection at Rest & in Transit**: S3 enforces default server-side encryption (`AES256`). All external communication uses TLS 1.3 / HTTPS.

---

## 3. Deployment Evidence Checklist

After completing the steps in [`deploy/aws/setup.md`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/deploy/aws/setup.md), record screenshots and output proofs below to verify deployment readiness.

### 1. Amazon ECR Repository & Docker Image
- [ ] Image built via multi-stage Dockerfile and pushed to ECR.
- **Repository URI**: `<AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/<ECR_REPOSITORY_NAME>`
- **Image Tag**: `latest`

```markdown
<!-- Empty slot: Insert screenshot of AWS ECR Console showing pushed image -->
![ECR Image Evidence](screenshots/01-ecr-image.png)
```

---

### 2. Amazon S3 Bucket & Model/Audio Artifacts
- [ ] S3 bucket created with public access blocked and versioning enabled.
- [ ] Model artifacts uploaded to `models/` prefix.
- [ ] Call audio upload prefix verified at `audio/calls/`.

```markdown
<!-- Empty slot: Insert screenshot of AWS S3 Console showing bucket prefixes -->
![S3 Objects Evidence](screenshots/02-s3-objects.png)
```

---

### 3. Amazon ECS Fargate Service Running
- [ ] ECS cluster created (`<ECS_CLUSTER_NAME>`).
- [ ] Service desired count = 1, running count = 1.
- [ ] Task status: `RUNNING`, Health Status: `HEALTHY`.

```markdown
<!-- Empty slot: Insert screenshot of AWS ECS Console showing Running Task -->
![ECS Service Evidence](screenshots/03-ecs-service.png)
```

---

### 4. Amazon CloudWatch Application Logs
- [ ] Log group `/ecs/<ECS_SERVICE_NAME>` receiving container logs.
- [ ] Logs show dataset loading, storage fallback check, and uvicorn running on port 8000.

```markdown
<!-- Empty slot: Insert screenshot of CloudWatch Logs stream -->
![CloudWatch Logs Evidence](screenshots/04-cloudwatch-logs.png)
```

---

### 5. GitHub Actions Automated CI/CD Run
- [ ] Push to `main` branch triggers `.github/workflows/deploy.yml`.
- [ ] OIDC authentication succeeds without static keys.
- [ ] Image built, pushed to ECR, and ECS service updated successfully.

```markdown
<!-- Empty slot: Insert screenshot of successful GitHub Actions run -->
![GitHub Actions Evidence](screenshots/05-github-actions.png)
```

---

### 6. Live Application Health URL Verification
- [ ] Health endpoint responds with HTTP 200:
  ```bash
  curl -i https://<YOUR_ENDPOINT_OR_ALB_OR_TUNNEL>/health
  ```
- **Expected Response**:
  ```json
  {
    "status": "healthy",
    "service": "kisan-ai-backend",
    "version": "1.0.0",
    "timestamp": "2026-10-23T18:00:00.000000"
  }
  ```

```markdown
<!-- Empty slot: Insert screenshot of terminal or browser verifying /health -->
![Health Check Evidence](screenshots/06-health-check.png)
```

---

## 4. Scaling & Memory Optimization

- **Default Lightweight Mode (0.25 vCPU / 0.5 GB RAM)**:
  Runs the FastAPI pipeline with rule-based intent routing (`INTENT_BACKEND=rules`), XGBoost / RandomForest crop models, FAISS vector retrieval, and live external APIs (Sarvam, Groq, WeatherAPI). Fits comfortably inside 512 MB.
- **Full IndicBERT Neural Mode (1.0 vCPU / 2.0 GB RAM)**:
  To load the fine-tuned 1.1 GB `model.safetensors` transformer directly into memory, update `cpu: "1024"`, `memory: "2048"`, and set `INTENT_BACKEND="bert"` in [`deploy/aws/ecs-task-definition.json`](file:///c:/Users/Lokesh%20S%20M/Desktop/SIH%202026/KISAN-AI/deploy/aws/ecs-task-definition.json).
