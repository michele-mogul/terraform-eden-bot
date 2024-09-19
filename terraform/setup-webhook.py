import getopt
import json
import os
import requests
import sys
import requests


def print_help():
    print('''
Usage: setup-webhook.py [options]

setup_webhook -- Setup Telegram webhook URL

Options:
  -h, --help            Show this help message and exit
  -w <webhook #>, --webhook=<webhook #>
                        Required argument: Webhook URL to set
  -t <token #>, --token=<token #>
                        Required argument: Telegram Bot Token 
''')


def register_webhook(webhook, token, type):
    r = requests.get(
        f'https://api.telegram.org/bot{token}/setWebhook?url={webhook}')
    print(r.json())

def main(argv=None):
    '''
    Main function: work with command line options and send an HTTPS request to the Telegram API
    '''

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'w:t:',
                                   ['help', 'webhook='])
    except getopt.GetoptError as err:
        # Print help information and exit:
        print(str(err))
        print_help()
        sys.exit(2)

    # Initialize parameters
    webhook = None
    token = None

    # Parse command line options
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print_help()
            sys.exit()
        elif opt in ('-w', '--webhook'):
            webhook = arg
        elif opt in ('-t', '--token'):
            token = arg

    # Enforce required arguments
    if not webhook or not type:
        print_help()
        sys.exit(4)

    # Enforce required arguments
    if not token or not type:
        print_help()
        sys.exit(4)

    register_webhook(webhook, token, type)


if __name__ == '__main__':
    sys.exit(main())
