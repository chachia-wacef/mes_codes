import boto3
from botocore.exceptions import ClientError

def send_status_email(subject, body_html):
    client = boto3.client('ses', region_name='eu-west-1') # Utilisez votre région
    
    try:
        response = client.send_email(
            Destination={'ToAddresses': ['destinataire@exemple.com']},
            Message={
                'Body': {
                    'Html': {'Charset': "UTF-8", 'Data': body_html},
                },
                'Subject': {'Charset': "UTF-8", 'Data': subject},
            },
            Source="votre-email-verifie@domaine.com",
        )
        print(f"Email envoyé ! ID: {response['MessageId']}")
    except ClientError as e:
        print(f"Erreur SES: {e.response['Error']['Message']}")