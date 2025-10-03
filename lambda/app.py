import json
import os
import hmac
import hashlib
import base64
import urllib.request
import urllib.error
from typing import Dict, Any, Tuple


def verify_shopify_signature(data: bytes, hmac_header: str, secret: str) -> bool:
    """
    Verify the HMAC signature from Shopify webhook.
    
    Args:
        data: Raw request body as bytes
        hmac_header: The X-Shopify-Hmac-SHA256 header value
        secret: Shopify webhook secret
    
    Returns:
        bool: True if signature is valid, False otherwise
    """
    try:
        # Compute HMAC
        computed_hmac = hmac.new(
            secret.encode('utf-8'),
            data,
            hashlib.sha256
        ).digest()
        
        # Encode as base64
        computed_hmac_b64 = base64.b64encode(computed_hmac).decode('utf-8')
        
        # Compare with provided HMAC
        return hmac.compare_digest(computed_hmac_b64, hmac_header)
    except Exception as e:
        print(f"Error verifying signature: {str(e)}")
        return False


def forward_to_maistro(
    payload: bytes,
    api_key: str,
    override_agent: str,
    debug: str,
    instance_id: str = "my-instance"
) -> Tuple[int, str]:
    """
    Forward the webhook payload to Maistro API using headers.
    
    Args:
        payload: The webhook payload as bytes
        api_key: Maistro API key
        override_agent: Override agent value
        debug: Debug flag value
        instance_id: Maistro instance ID
    
    Returns:
        Tuple of (status_code, response_body)
    """
    url = f"https://api-usw.neuralseek.com/v1/{instance_id}/maistro"
    
    headers = {
        'Content-Type': 'application/json',
        'apikey': api_key,
        'overrideschema': 'true',
        'overrideagent': override_agent,
        'debug': debug
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=25) as response:
            status_code = response.status
            response_body = response.read().decode('utf-8')
            return status_code, response_body
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        print(f"HTTP Error forwarding to Maistro: {e.code} - {error_body}")
        return e.code, error_body
    except urllib.error.URLError as e:
        print(f"URL Error forwarding to Maistro: {str(e)}")
        return 502, json.dumps({"error": "Failed to connect to Maistro API"})
    except Exception as e:
        print(f"Unexpected error forwarding to Maistro: {str(e)}")
        return 500, json.dumps({"error": str(e)})


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for Shopify webhook processing.
    
    Args:
        event: API Gateway event
        context: Lambda context
    
    Returns:
        API Gateway response
    """
    print(f"Received webhook event")
    
    # Get environment variables
    shopify_secret = os.environ.get('SHOPIFY_SECRET')
    maistro_api_key = os.environ.get('MAISTRO_API_KEY')
    maistro_instance_id = os.environ.get('MAISTRO_INSTANCE_ID', 'my-instance')
    maistro_override_agent = os.environ.get('MAISTRO_OVERRIDE_AGENT', 'test_order_fulfilled')
    maistro_debug = os.environ.get('MAISTRO_DEBUG', 'false')
    
    if not shopify_secret or not maistro_api_key or not maistro_instance_id:
        print("Error: Missing required environment variables")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Configuration error'})
        }
    
    # Extract headers and body
    headers = event.get('headers', {})
    
    # Handle case-insensitive headers
    headers_lower = {k.lower(): v for k, v in headers.items()}
    hmac_header = headers_lower.get('x-shopify-hmac-sha256')
    
    if not hmac_header:
        print("Error: Missing X-Shopify-Hmac-SHA256 header")
        return {
            'statusCode': 401,
            'body': json.dumps({'error': 'Missing signature header'})
        }
    
    # Get raw body
    body = event.get('body', '')
    is_base64 = event.get('isBase64Encoded', False)
    
    if is_base64:
        body_bytes = base64.b64decode(body)
    else:
        body_bytes = body.encode('utf-8')
    
    # Verify Shopify signature
    if not verify_shopify_signature(body_bytes, hmac_header, shopify_secret):
        print("Error: Invalid webhook signature")
        return {
            'statusCode': 401,
            'body': json.dumps({'error': 'Invalid signature'})
        }
    
    print("Webhook signature verified successfully")
    
    # Log webhook topic if available
    topic = headers_lower.get('x-shopify-topic', 'unknown')
    shop_domain = headers_lower.get('x-shopify-shop-domain', 'unknown')
    print(f"Webhook topic: {topic}, Shop: {shop_domain}")
    
    # Forward to Maistro
    status_code, response_body = forward_to_maistro(
        body_bytes,
        maistro_api_key,
        maistro_override_agent,
        maistro_debug,
        maistro_instance_id
    )
    
    if 200 <= status_code < 300:
        print(f"Successfully forwarded to Maistro. Status: {status_code}")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Webhook processed successfully',
                'maistro_status': status_code
            })
        }
    else:
        print(f"Failed to forward to Maistro. Status: {status_code}")
        return {
            'statusCode': 200,  # Still return 200 to Shopify to prevent retries
            'body': json.dumps({
                'message': 'Webhook received but forwarding failed',
                'maistro_status': status_code,
                'error': response_body
            })
        }