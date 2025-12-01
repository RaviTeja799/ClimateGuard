#!/bin/bash
# ClimateGuard - Cloud Run Deployment Script
# This script deploys the ClimateGuard multi-agent system to Google Cloud Run
# Provides bonus points for the Kaggle Agents Intensive Capstone

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="climateguard-agent"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}ClimateGuard Cloud Run Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not installed${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker not installed${NC}"
    echo "Install from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Verify authentication
echo -e "\n${YELLOW}Verifying GCP authentication...${NC}"
if ! gcloud auth print-identity-token &> /dev/null; then
    echo "Please authenticate with GCP:"
    gcloud auth login
fi

# Set project
echo -e "\n${YELLOW}Setting GCP project to: ${PROJECT_ID}${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "\n${YELLOW}Enabling required APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    aiplatform.googleapis.com \
    --quiet

# Build Docker image
echo -e "\n${YELLOW}Building Docker image...${NC}"
docker build -t ${IMAGE_NAME}:latest -f deploy/Dockerfile .

# Push to Container Registry
echo -e "\n${YELLOW}Pushing image to Container Registry...${NC}"
gcloud auth configure-docker --quiet
docker push ${IMAGE_NAME}:latest

# Deploy to Cloud Run
echo -e "\n${YELLOW}Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --concurrency 80 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY}" \
    --set-env-vars "CLIMATIQ_API_KEY=${CLIMATIQ_API_KEY}" \
    --set-env-vars "ELECTRICITY_MAPS_API_KEY=${ELECTRICITY_MAPS_API_KEY}" \
    --set-env-vars "ENVIRONMENT=production"

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\nService URL: ${SERVICE_URL}"
echo -e "\nTest the deployment:"
echo -e "  curl ${SERVICE_URL}/health"
echo -e "\nView logs:"
echo -e "  gcloud run logs read --service ${SERVICE_NAME} --region ${REGION}"

# Verify deployment
echo -e "\n${YELLOW}Verifying deployment...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" ${SERVICE_URL}/health || echo "000")

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓ Health check passed!${NC}"
else
    echo -e "${YELLOW}⚠ Health check returned: ${HTTP_CODE}${NC}"
    echo "The service may still be starting up. Try again in a few seconds."
fi

echo -e "\n${GREEN}ClimateGuard is ready to help reduce carbon footprints! 🌍${NC}"
