from fastapi import APIRouter, Depends, HTTPException, Response
from ..auth_helpers import get_google_credentials
from ..auth_helpers import authorize_admin
from ..models import MailPayload, AccessTokenPayload

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from email.message import EmailMessage
import base64

router = APIRouter()

@router.post('/send-mail/')
def send_mail(payload: MailPayload, token: AccessTokenPayload = Depends(authorize_admin)):
    try:
        creds = get_google_credentials(payload.sent_by)
    except FileNotFoundError:
        raise HTTPException(500, "Internal server error")

    try:
        # Call the Gmail API
        service = build('gmail', 'v1', credentials=creds)
        message = EmailMessage()

        message['Subject'] = payload.subject
        message.set_content(payload.content)
        message['To'] = payload.to
        message['From'] = payload.sent_by

         # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {
            'raw': encoded_message
        }
        # pylint: disable=E1101
        send_message = service.users().messages().send(userId="me", body=create_message).execute()
    except HttpError as error:
        raise HTTPException(500, 'Internal server error when communicating with google')
    except RefreshError:
        raise HTTPException(400, 'Invalid sent_from email')

    return Response(status_code=200)