#!/bin/bash
set -e

echo "================================================"
echo "Motiv8 Complete Setup Script"
echo "================================================"

STACK_NAME="motiv8-ec2-instances"
DOMAIN="motiv8me.io"

# Step 1: Wait for EC2 stack to complete
echo "Step 1: Waiting for EC2 stack to complete..."
echo "(This may take 5-10 minutes)"
aws cloudformation wait stack-create-complete --stack-name $STACK_NAME
echo "✓ EC2 stack created successfully!"

# Step 2: Get EC2 instance details
echo ""
echo "Step 2: Getting EC2 instance details..."
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`WebAppInstanceId`].OutputValue' \
  --output text)

PUBLIC_IP=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`WebAppPublicIP`].OutputValue' \
  --output text)

echo "✓ Instance ID: $INSTANCE_ID"
echo "✓ Public IP: $PUBLIC_IP"

# Step 3: Create DNS records
echo ""
echo "Step 3: Creating DNS records..."

# Get hosted zone ID
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='${DOMAIN}.'].Id" \
  --output text | cut -d'/' -f3)

if [ -z "$HOSTED_ZONE_ID" ]; then
    echo "ERROR: Hosted zone for $DOMAIN not found!"
    echo "Please create it in Route 53 first."
    exit 1
fi

echo "✓ Hosted Zone ID: $HOSTED_ZONE_ID"

# Create/Update A record for root domain
echo "Creating A record for $DOMAIN..."
cat > /tmp/dns-change-root.json <<EOF
{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "${DOMAIN}",
      "Type": "A",
      "TTL": 300,
      "ResourceRecords": [{"Value": "${PUBLIC_IP}"}]
    }
  }]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch file:///tmp/dns-change-root.json

# Create/Update A record for www subdomain
echo "Creating A record for www.${DOMAIN}..."
cat > /tmp/dns-change-www.json <<EOF
{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "www.${DOMAIN}",
      "Type": "A",
      "TTL": 300,
      "ResourceRecords": [{"Value": "${PUBLIC_IP}"}]
    }
  }]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch file:///tmp/dns-change-www.json

echo "✓ DNS records created!"

# Step 4: Copy deployment script to EC2
echo ""
echo "Step 4: Uploading deployment script to EC2..."

# Upload via S3 (works without SSH)
TEMP_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name production-motiv8-main \
  --query 'Stacks[0].Outputs[?OutputKey==`UploadsBucketName`].OutputValue' \
  --output text)

aws s3 cp ../deploy-to-ec2.sh s3://$TEMP_BUCKET/deploy-to-ec2.sh

echo "✓ Deployment script uploaded to S3"

# Step 5: Wait for instance to be ready for SSM
echo ""
echo "Step 5: Waiting for instance to be ready for Systems Manager..."
echo "(This may take a few minutes for the instance to boot and register)"

MAX_WAIT=300  # 5 minutes
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    INSTANCE_STATUS=$(aws ssm describe-instance-information \
      --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
      --query 'InstanceInformationList[0].PingStatus' \
      --output text 2>/dev/null)

    if [ "$INSTANCE_STATUS" = "Online" ]; then
        echo "✓ Instance is ready for Systems Manager!"
        break
    fi

    echo "  Waiting for instance to be online... ($WAIT_COUNT seconds)"
    sleep 10
    WAIT_COUNT=$((WAIT_COUNT + 10))
done

if [ "$INSTANCE_STATUS" != "Online" ]; then
    echo "⚠ Instance not ready for SSM yet. You may need to wait longer."
    echo "  Try running the deployment script manually later:"
    echo "  aws ssm start-session --target $INSTANCE_ID"
    exit 1
fi

# Step 6: Run deployment via SSM
echo ""
echo "Step 6: Running deployment on EC2..."
echo "(This will take several minutes - installing packages, building frontend, etc.)"

SSM_COMMAND_ID=$(aws ssm send-command \
  --instance-ids $INSTANCE_ID \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[
    'aws s3 cp s3://$TEMP_BUCKET/deploy-to-ec2.sh /tmp/deploy-to-ec2.sh',
    'chmod +x /tmp/deploy-to-ec2.sh',
    'sudo /tmp/deploy-to-ec2.sh'
  ]" \
  --output text \
  --query 'Command.CommandId')

echo "✓ Deployment command sent (ID: $SSM_COMMAND_ID)"
echo "  Waiting for deployment to complete..."

# Wait for command to complete
aws ssm wait command-executed \
  --command-id $SSM_COMMAND_ID \
  --instance-id $INSTANCE_ID

# Get command output
echo ""
echo "Deployment output:"
echo "================================================"
aws ssm get-command-invocation \
  --command-id $SSM_COMMAND_ID \
  --instance-id $INSTANCE_ID \
  --query 'StandardOutputContent' \
  --output text

echo "================================================"

# Step 7: Wait for DNS propagation
echo ""
echo "Step 7: Checking DNS propagation..."
echo "Waiting for DNS to propagate (this can take 5-60 minutes)..."
echo "Checking every 30 seconds..."

MAX_ATTEMPTS=120  # 60 minutes max
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if dig +short $DOMAIN | grep -q "$PUBLIC_IP"; then
        echo "✓ DNS propagated successfully!"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo "  Attempt $ATTEMPT/$MAX_ATTEMPTS - DNS not ready yet..."
    sleep 30
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "⚠ DNS propagation taking longer than expected"
    echo "  You can continue manually once DNS resolves"
fi

# Step 8: Setup SSL
echo ""
echo "Step 8: Setting up SSL certificate..."
echo "Running certbot..."

SSL_COMMAND_ID=$(aws ssm send-command \
  --instance-ids $INSTANCE_ID \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[
    'sudo certbot certonly --webroot --webroot-path=/var/www/letsencrypt --email jacksoncook73@gmail.com --agree-tos --no-eff-email -d $DOMAIN -d www.$DOMAIN --non-interactive',
    'sudo certbot install --cert-name $DOMAIN --nginx --non-interactive',
    'sudo systemctl reload nginx'
  ]" \
  --output text \
  --query 'Command.CommandId')

echo "  Waiting for SSL setup..."
aws ssm wait command-executed \
  --command-id $SSL_COMMAND_ID \
  --instance-id $INSTANCE_ID

# Get SSL setup output
echo ""
echo "SSL setup output:"
echo "================================================"
aws ssm get-command-invocation \
  --command-id $SSL_COMMAND_ID \
  --instance-id $INSTANCE_ID \
  --query 'StandardOutputContent' \
  --output text
echo "================================================"

# Final summary
echo ""
echo "================================================"
echo "🎉 Setup Complete!"
echo "================================================"
echo ""
echo "Your application is now live at:"
echo "  https://$DOMAIN"
echo "  https://www.$DOMAIN"
echo ""
echo "Backend API: https://$DOMAIN/api/hello"
echo "EC2 Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo ""
echo "To check logs:"
echo "  aws ssm start-session --target $INSTANCE_ID"
echo "  sudo journalctl -u motiv8-backend -f"
echo ""
echo "To redeploy code:"
echo "  Push changes to GitHub"
echo "  Run: aws ssm send-command --instance-ids $INSTANCE_ID --document-name 'AWS-RunShellScript' --parameters 'commands=[\"cd /app && sudo git pull && sudo systemctl restart motiv8-backend\"]'"
echo "================================================"
