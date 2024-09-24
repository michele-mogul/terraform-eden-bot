import json
import os
import urllib3
from telegram.ext import Application


BOT_TOKEN = os.environ.get('telegram_key')


def send_reply(chat_id, message):
    reply = {
        "chat_id": chat_id,
        "text": message
    }

    http = urllib3.PoolManager()
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    encoded_data = json.dumps(reply).encode('utf-8')
    http.request('POST', url, body=encoded_data, headers={'Content-Type': 'application/json'})

    print(f"*** Reply : {encoded_data}")


def lambda_handler(event, context):
    Application.run_webhook(
        listen='0.0.0.0',
        port=80,
        secret_token=BOT_TOKEN,
        webhook_url=event.requestContext.domainName
    )

    return {
        'statusCode': 200,
        'body': json.dumps(f'Message processed successfully with domain name: {event.requestContext.domainName}')
    }


