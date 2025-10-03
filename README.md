# Shopify Webhook Handler for Maistro API

This AWS SAM application receives Shopify webhooks, verifies their HMAC signature, and forwards them to the NeuralSeek Maistro API using header-based parameters.

## Architecture

- **API Gateway**: Public endpoint for Shopify webhooks
- **Lambda Function**: Python 3.13 function that:
  - Verifies Shopify HMAC-SHA256 signatures
  - Forwards valid webhooks to Maistro API
  - Uses headers for API configuration (apikey, overrideschema, overrideagent, debug)

## Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate credentials
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Python 3.13
- Shopify webhook secret
- Maistro API key

## Project Structure

```
shopify-webhook-handler/
│
├── template.yaml          # SAM template (IaC)
├── lambda/
│   └── app.py             # Lambda function code
└── README.md              # This file
```

## Deployment

### 1. Build the SAM application

```bash
sam build
```

### 2. Deploy with guided prompts

```bash
sam deploy --guided
```

During the guided deployment, you'll be prompted for:

- **Stack Name**: Name for your CloudFormation stack (e.g., `shopify-webhook-handler`)
- **AWS Region**: Your preferred region (e.g., `us-east-1`)
- **ShopifySecret**: Your Shopify webhook secret (found in Shopify Admin → Settings → Notifications)
- **MaistroApiKey**: Your Maistro API key
- **MaistroInstanceId**: Your Maistro instance ID (e.g., `my-instance`)
- **MaistroOverrideAgent**: Override agent value (default: `test_order_fulfilled`)
- **MaistroDebug**: Enable debug mode (default: `false`, options: `true` or `false`)
- Confirm changes and allow SAM to create IAM roles

### 3. Save configuration

SAM will save your configuration to `samconfig.toml` for future deployments.

### 4. Get the webhook URL

After deployment, SAM will output the webhook URL:

```
WebhookApiUrl: https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/webhook
```

## Configure Shopify Webhook

1. Go to your Shopify Admin
2. Navigate to **Settings → Notifications**
3. Scroll to **Webhooks**
4. Click **Create webhook**
5. Configure:
   - **Event**: Select your desired event (e.g., Order creation)
   - **Format**: JSON
   - **URL**: Paste the `WebhookApiUrl` from SAM output
   - **API version**: Latest stable version
6. Click **Save**

## Testing

### Test locally with SAM

```bash
sam local invoke ShopifyWebhookFunction --event events/test-event.json
```

### Create a test event file

Create `events/test-event.json`:

```json
{
  "body": "{\"id\":123,\"order_number\":1001}",
  "headers": {
    "X-Shopify-Hmac-SHA256": "your-test-signature",
    "X-Shopify-Topic": "orders/create",
    "X-Shopify-Shop-Domain": "your-shop.myshopify.com"
  }
}
```

### Monitor logs

```bash
sam logs -n ShopifyWebhookFunction --tail
```

Or view in AWS CloudWatch:
```bash
aws logs tail /aws/lambda/shopify-webhook-handler-ShopifyWebhookFunction-xxxxx --follow
```

## Configuration Parameters

### Environment Variables (configured during deployment)

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SHOPIFY_SECRET` | Shopify webhook secret for signature verification | Yes | - |
| `MAISTRO_API_KEY` | Maistro API authentication key | Yes | - |
| `MAISTRO_INSTANCE_ID` | Maistro instance ID | Yes | - |
| `MAISTRO_OVERRIDE_AGENT` | Override agent parameter for Maistro | No | `test_order_fulfilled` |
| `MAISTRO_DEBUG` | Enable debug mode | No | `false` |

### Maistro API Headers

The Lambda function sends the following headers to Maistro:

- `apikey`: Your Maistro API key
- `overrideschema`: Always set to `true`
- `overrideagent`: Value from `MAISTRO_OVERRIDE_AGENT` env var
- `debug`: Value from `MAISTRO_DEBUG` env var
- `Content-Type`: `application/json`

## Update Deployment

To update the stack with new configuration:

```bash
sam build
sam deploy
```

Or to update specific parameters:

```bash
sam deploy --parameter-overrides \
  ShopifySecret="new-secret" \
  MaistroInstanceId="your-instance" \
  MaistroOverrideAgent="new-agent"
```

## Security Considerations

- Webhook signatures are verified using HMAC-SHA256
- Secrets are marked as `NoEcho` in CloudFormation (not displayed in console)
- API keys are stored as environment variables (consider using AWS Secrets Manager for production)
- Lambda has minimal IAM permissions
- CloudWatch logs retain for 7 days (configurable in template)

## Troubleshooting

### Webhook signature verification fails

- Verify the `SHOPIFY_SECRET` matches your Shopify webhook secret
- Ensure the webhook secret hasn't been regenerated in Shopify
- Check CloudWatch logs for detailed error messages

### Maistro forwarding fails

- Verify `MAISTRO_API_KEY` is correct
- Verify `MAISTRO_INSTANCE_ID` matches your NeuralSeek instance
- Review CloudWatch logs for HTTP error codes
- Ensure Lambda has internet access (check VPC configuration if applicable)

### View logs

```bash
aws logs tail /aws/lambda/<function-name> --follow --format short
```

## Cleanup

To delete the stack and all resources:

```bash
sam delete
```

## Customization

### Add additional headers

Modify the `headers` dictionary in `forward_to_maistro` function in `lambda/app.py`.

## Support

For issues related to:
- **AWS SAM/Lambda**: Check [AWS SAM documentation](https://docs.aws.amazon.com/serverless-application-model/)
- **Shopify Webhooks**: Check [Shopify webhook documentation](https://shopify.dev/docs/api/admin-rest/latest/resources/webhook)
- **Maistro API**: Contact NeuralSeek support

This code was generated or assisted by AI (Claude). The author(s) make no claim of originality and provide it as-is, with no warranty or guarantees of correctness, fitness for purpose, or ownership.
