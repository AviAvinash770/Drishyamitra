"""
Sharing service for Drishyamitra.

Handles photo delivery via e-mail and WhatsApp using active SMTP/Gmail and Twilio integrations.
"""

import os
import logging
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime, timezone

from database.db import db
from models.sharing import DeliveryHistory

logger = logging.getLogger(__name__)


def _send_real_email(recipient, person_name, photo_paths):
    """Send an email with photo attachments via SMTP/Gmail."""
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port_str = os.environ.get("SMTP_PORT", "465")

    if not smtp_user or not smtp_password:
        logger.warning("[SMTP] SMTP_USER or SMTP_PASSWORD not set in .env. Skipping real email send.")
        return False

    try:
        primary_port = int(smtp_port_str)
    except ValueError:
        primary_port = 465

    fallback_port = 587 if primary_port == 465 else 465

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = recipient
    msg['Subject'] = f"Drishyamitra — Photos shared with you"

    body_text = f"Hi,\n\nHere are the photos of '{person_name or 'selected collection'}' shared via Drishyamitra AI Assistant.\n\nEnjoy!"
    msg.attach(MIMEText(body_text, 'plain'))

    for path in photo_paths:
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    img_data = f.read()
                    filename = os.path.basename(path)
                    image = MIMEImage(img_data, name=filename)
                    image.add_header('Content-Disposition', 'attachment', filename=filename)
                    msg.attach(image)
            except Exception as e:
                logger.error("[SMTP] Failed to attach file %s: %s", path, e)

    def try_send(port):
        logger.info("[SMTP] Attempting email dispatch via %s:%d", smtp_server, port)
        if port == 465:
            with smtplib.SMTP_SSL(smtp_server, port, timeout=10) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, recipient, msg.as_string())
        else:
            with smtplib.SMTP(smtp_server, port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, recipient, msg.as_string())
        return True

    # Try primary port first
    try:
        if try_send(primary_port):
            logger.info("[SMTP] Successfully sent email to %s using primary port %d", recipient, primary_port)
            return True
    except Exception as exc:
        logger.warning("[SMTP] Primary port %d failed: %s. Trying fallback port %d...", primary_port, exc, fallback_port)
        # Try fallback port
        try:
            if try_send(fallback_port):
                logger.info("[SMTP] Successfully sent email to %s using fallback port %d", recipient, fallback_port)
                return True
        except Exception as exc_fallback:
            logger.error("[SMTP] Fallback port %d also failed: %s", fallback_port, exc_fallback)
            
    return False


def _send_real_whatsapp(recipient, person_name, photo_paths):
    """Send a WhatsApp message with an optional media link via Twilio."""
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_whatsapp = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    public_base_url = os.environ.get("PUBLIC_BASE_URL")

    if not account_sid or not auth_token:
        logger.warning("[TWILIO] TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN not set in .env. Skipping real WhatsApp send.")
        return False

    # Standardize phone number format
    to_number = recipient
    if not to_number.startswith("whatsapp:"):
        clean_num = "".join(c for c in to_number if c.isdigit() or c == '+')
        if not clean_num.startswith("+"):
            if len(clean_num) == 10:
                clean_num = "+91" + clean_num
            else:
                clean_num = "+" + clean_num
        to_number = f"whatsapp:{clean_num}"

    body_text = f"Hi! Here are the photos of '{person_name or 'selected collection'}' shared via Drishyamitra!"
    
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    
    # Twilio allows sending an image link if served publicly
    media_url = None
    if public_base_url and photo_paths:
        first_img = os.path.basename(photo_paths[0])
        media_url = f"{public_base_url.rstrip('/')}/api/photos/file/{first_img}"
        body_text += f"\nView all {len(photo_paths)} photos."

    payload = {
        "From": from_whatsapp,
        "To": to_number,
        "Body": body_text
    }
    if media_url:
        payload["MediaUrl"] = media_url

    try:
        res = requests.post(
            url,
            data=payload,
            auth=(account_sid, auth_token),
            timeout=10
        )
        if res.status_code in [200, 201]:
            logger.info("[TWILIO] Successfully sent WhatsApp message to %s", to_number)
            return True
        else:
            logger.error("[TWILIO] Twilio API returned error: %s", res.text)
            return False
    except Exception as exc:
        logger.error("[TWILIO] Failed to send WhatsApp message to %s: %s", recipient, exc)
        return False


class SharingService:
    """Handles photo sharing via email and WhatsApp."""

    @staticmethod
    def send_email(recipient, person_name, photo_paths, user_id=None):
        """Send photos via e-mail (SMTP/Gmail) and record delivery."""
        photo_count = len(photo_paths) if photo_paths else 0

        try:
            logger.info(
                "EMAIL sharing – sending %d photo(s) to '%s' <%s> for user %s.",
                photo_count,
                person_name,
                recipient,
                user_id,
            )

            # Send the real email in the background/sync
            success = _send_real_email(recipient, person_name, photo_paths)
            status = 'delivered' if success else 'failed'

            delivery = DeliveryHistory(
                recipient=recipient,
                platform='email',
                person_name=person_name or 'Selected Photos',
                photo_count=photo_count,
                status=status,
                user_id=user_id,
            )
            db.session.add(delivery)
            db.session.commit()

            return _serialise_delivery(delivery)

        except Exception as exc:
            db.session.rollback()
            logger.error("Failed to record email delivery: %s", exc)
            raise

    @staticmethod
    def send_whatsapp(recipient, person_name, photo_paths, user_id=None):
        """Send photos via WhatsApp (Twilio API) and record delivery."""
        photo_count = len(photo_paths) if photo_paths else 0

        try:
            logger.info(
                "WHATSAPP sharing – sending %d photo(s) to '%s' (%s) for user %s.",
                photo_count,
                person_name,
                recipient,
                user_id,
            )

            # Send the real WhatsApp message
            success = _send_real_whatsapp(recipient, person_name, photo_paths)
            status = 'delivered' if success else 'failed'

            delivery = DeliveryHistory(
                recipient=recipient,
                platform='whatsapp',
                person_name=person_name or 'Selected Photos',
                photo_count=photo_count,
                status=status,
                user_id=user_id,
            )
            db.session.add(delivery)
            db.session.commit()

            return _serialise_delivery(delivery)

        except Exception as exc:
            db.session.rollback()
            logger.error("Failed to record WhatsApp delivery: %s", exc)
            raise

    @staticmethod
    def get_delivery_history(user_id=None):
        """
        Retrieve delivery history records.

        Args:
            user_id (int | None): If provided, filter by the sending user's ID.
                If ``None``, return **all** delivery records.

        Returns:
            list[dict]: List of serialised ``DeliveryHistory`` records ordered
            by most-recent first.
        """
        try:
            query = DeliveryHistory.query.order_by(
                DeliveryHistory.id.desc()
            )
            if user_id is not None:
                query = query.filter_by(user_id=user_id)

            records = query.all()
            return [_serialise_delivery(r) for r in records]

        except Exception as exc:
            logger.error("Failed to fetch delivery history: %s", exc)
            return []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _serialise_delivery(delivery):
    """
    Convert a ``DeliveryHistory`` ORM object to a plain dict.

    Args:
        delivery (DeliveryHistory): The database record.

    Returns:
        dict: JSON-safe representation.
    """
    return {
        'id': delivery.id,
        'recipient': delivery.recipient,
        'platform': delivery.platform,
        'person_name': delivery.person_name,
        'photo_count': delivery.photo_count,
        'status': delivery.status,
        'user_id': delivery.user_id,
    }
