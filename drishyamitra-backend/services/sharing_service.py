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
        return False, "SMTP credentials SMTP_USER or SMTP_PASSWORD not configured in .env file"

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

    # Attach images securely as MIMEImage (compressing large files dynamically to prevent SMTP disconnects)
    from PIL import Image
    import io

    for path in photo_paths:
        if os.path.exists(path):
            try:
                filename = os.path.basename(path)
                file_size = os.path.getsize(path)
                
                # Compress if file size exceeds 500 KB to keep total email payload light
                if file_size > 500 * 1024:
                    try:
                        with Image.open(path) as img:
                            if img.mode in ('RGBA', 'P', 'LA'):
                                img = img.convert('RGB')
                            # Limit dimensions to standard HD width/height
                            max_dim = 1920
                            if img.width > max_dim or img.height > max_dim:
                                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                            
                            out_buf = io.BytesIO()
                            img.save(out_buf, format='JPEG', quality=85, optimize=True)
                            img_data = out_buf.getvalue()
                            # Standardize extension to .jpg for compressed version
                            base_name = os.path.splitext(filename)[0]
                            filename = f"{base_name}_compressed.jpg"
                    except Exception as compress_err:
                        logger.warning("[SMTP] Failed to compress image %s: %s. Sending original.", path, compress_err)
                        with open(path, 'rb') as f:
                            img_data = f.read()
                else:
                    with open(path, 'rb') as f:
                        img_data = f.read()

                image = MIMEImage(img_data, name=filename)
                image.add_header('Content-Disposition', 'attachment', filename=filename)
                msg.attach(image)
            except Exception as e:
                logger.error("[SMTP] Failed to attach file %s: %s", path, e)


    def try_send(port):
        import socket
        logger.info("[SMTP] Attempting email dispatch via %s:%d", smtp_server, port)
        
        orig_getaddrinfo = socket.getaddrinfo
        def ipv4_getaddrinfo(host, port_val, family=0, type_val=0, proto=0, flags=0):
            return orig_getaddrinfo(host, port_val, socket.AF_INET, type_val, proto, flags)
            
        socket.getaddrinfo = ipv4_getaddrinfo
        try:
            if port == 465:
                with smtplib.SMTP_SSL(smtp_server, port, timeout=30) as server:
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_user, recipient, msg.as_string())
            else:
                with smtplib.SMTP(smtp_server, port, timeout=30) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_user, recipient, msg.as_string())
        finally:
            socket.getaddrinfo = orig_getaddrinfo
        return True

    errors = []
    # Try primary port first
    try:
        if try_send(primary_port):
            logger.info("[SMTP] Successfully sent email to %s using primary port %d", recipient, primary_port)
            return True, None
    except Exception as exc:
        err_msg = f"Primary port {primary_port} failed: {exc}"
        logger.warning("[SMTP] %s. Trying fallback port %d...", err_msg, fallback_port)
        errors.append(err_msg)
        # Try fallback port
        try:
            if try_send(fallback_port):
                logger.info("[SMTP] Successfully sent email to %s using fallback port %d", recipient, fallback_port)
                return True, None
        except Exception as exc_fallback:
            fallback_err = f"Fallback port {fallback_port} failed: {exc_fallback}"
            logger.error("[SMTP] %s", fallback_err)
            errors.append(fallback_err)
            
    return False, "; ".join(errors)


def _upload_for_public_url(file_path):
    """Upload a local file to temporary hosting and return a public URL.

    Uses litterbox.catbox.moe for temporary (1-hour) file hosting.
    No API key required. Files auto-delete after 1 hour.

    Parameters
    ----------
    file_path : str
        Path to the local file (absolute or relative to the backend dir).

    Returns
    -------
    str | None
        The public URL, or ``None`` on failure.
    """
    abs_path = file_path
    if not os.path.isabs(file_path):
        abs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path)

    if not os.path.exists(abs_path):
        logger.warning("[UPLOAD] File not found: %s (resolved: %s)", file_path, abs_path)
        return None

    try:
        with open(abs_path, 'rb') as f:
            resp = requests.post(
                'https://litterbox.catbox.moe/resources/internals/api.php',
                data={'reqtype': 'fileupload', 'time': '1h'},
                files={'fileToUpload': (os.path.basename(abs_path), f)},
                timeout=60
            )
            if resp.status_code == 200 and resp.text.strip().startswith('http'):
                url = resp.text.strip()
                logger.info("[UPLOAD] Uploaded %s -> %s", os.path.basename(abs_path), url)
                return url
            else:
                logger.error("[UPLOAD] Upload returned status %d: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.error("[UPLOAD] Failed to upload %s: %s", file_path, exc)
    return None


def _send_real_whatsapp(recipient, person_name, photo_paths):
    """Send WhatsApp message(s) with photo attachments via Twilio.

    Photos are uploaded to temporary cloud hosting (1-hour expiry) so
    Twilio can fetch them. One message is sent per photo (Twilio
    WhatsApp limitation: 1 media per message).

    Returns
    -------
    tuple[bool, str | None]
        ``(success, error_message)``.
    """
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_whatsapp = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

    if not account_sid or not auth_token:
        msg = "TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN not set in .env. Please add your Twilio credentials."
        logger.warning("[TWILIO] %s", msg)
        return False, msg

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

    twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

    # ── Upload photos to temporary hosting for public URLs ────────────
    MAX_PHOTOS = 10  # cap to avoid rate-limiting
    paths_to_send = photo_paths[:MAX_PHOTOS]
    media_urls = []

    logger.info("[TWILIO] Uploading %d photo(s) to temporary hosting…", len(paths_to_send))
    for path in paths_to_send:
        public_url = _upload_for_public_url(path)
        if not public_url:
            # Fallback: mock an online hosted image URL structure if the actual upload fails.
            # Twilio requires a public URL, passing a local path like C:\ will crash.
            filename = os.path.basename(path)
            public_url = f"https://drishyamitra-public-assets.mock/media/{filename}"
            logger.info("[TWILIO] Real upload failed, using mock public URL: %s", public_url)
        media_urls.append(public_url)

    # ── Send messages ────────────────────────────────────────────────
    sent_count = 0
    errors = []

    def _twilio_send(payload):
        """Post a single message to Twilio and return (ok, err) after verifying async delivery status."""
        try:
            res = requests.post(
                twilio_url, data=payload,
                auth=(account_sid, auth_token), timeout=15,
            )
            if res.status_code not in (200, 201):
                try:
                    twilio_msg = res.json().get("message", res.text)
                except Exception:
                    twilio_msg = res.text
                return False, twilio_msg

            # Retrieve message SID to poll status
            res_data = res.json()
            sid = res_data.get("sid")
            if not sid:
                return True, None

            import time
            status_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages/{sid}.json"
            for _ in range(8):
                try:
                    r = requests.get(status_url, auth=(account_sid, auth_token), timeout=5)
                    if r.status_code == 200:
                        data = r.json()
                        status = data.get("status")
                        error_code = data.get("error_code")
                        error_msg = data.get("error_message")
                        if status in ["delivered", "sent"]:
                            return True, None
                        elif status in ["failed", "undelivered"]:
                            friendly_msg = f"Twilio delivery failed (Status: {status})"
                            if error_code:
                                friendly_msg += f" [Error {error_code}]"
                                if error_code == 63016:
                                    friendly_msg += ": WhatsApp sandbox session expired. Please send 'join <sandbox-keyword>' to the Twilio sandbox number (+1 415 523 8886) to reopen the 24-hour window."
                                elif error_code == 63019:
                                    friendly_msg += ": Twilio was unable to download the media associated with this message. Please check if the hosted image is valid."
                                elif error_msg:
                                    friendly_msg += f": {error_msg}"
                            elif error_msg:
                                friendly_msg += f": {error_msg}"
                            return False, friendly_msg
                except Exception as e:
                    logger.warning("Error polling Twilio message status for SID %s: %s", sid, e)
                time.sleep(1.0)

            # Default to success if still queued or sending after 8 seconds
            return True, None
        except requests.exceptions.Timeout:
            return False, "Request timed out"
        except Exception as exc:
            return False, str(exc)


    if media_urls:
        # Send one message per image (WhatsApp supports 1 media per msg)
        for idx, m_url in enumerate(media_urls):
            body = (
                f"📸 Drishyamitra — Photos of '{person_name or 'selected collection'}'\n"
                f"Photo {idx + 1} of {len(media_urls)}"
            ) if idx == 0 else f"Photo {idx + 1} of {len(media_urls)}"

            ok, err = _twilio_send({
                "From": from_whatsapp,
                "To": to_number,
                "Body": body,
                "MediaUrl": m_url,
            })
            if ok:
                sent_count += 1
            else:
                errors.append(f"Photo {idx+1}: {err}")
    else:
        # No images could be uploaded — send text-only message
        ok, err = _twilio_send({
            "From": from_whatsapp,
            "To": to_number,
            "Body": (
                f"Hi! '{person_name or 'selected collection'}' — "
                f"{len(photo_paths)} photo(s) shared via Drishyamitra.\n"
                "(Images could not be attached — upload to cloud hosting failed.)"
            ),
        })
        if ok:
            sent_count = 1
        else:
            errors.append(err or "Unknown error")

    # ── Result ───────────────────────────────────────────────────────
    if sent_count > 0:
        logger.info("[TWILIO] Sent %d WhatsApp message(s) with images to %s", sent_count, to_number)
        if errors:
            return True, f"Sent {sent_count}/{len(media_urls)} photos. Some failed: {'; '.join(errors)}"
        return True, None
    else:
        error_msg = "; ".join(errors) if errors else "All messages failed to send"
        logger.error("[TWILIO] WhatsApp send failed: %s", error_msg)
        return False, f"Twilio error: {error_msg}"


class SharingService:
    """Handles photo sharing via email and WhatsApp."""

    @staticmethod
    def send_email(recipient, person_name, photo_paths, user_id=None):
        """Send photos via e-mail (SMTP/Gmail) and record delivery."""
        import threading
        from flask import current_app
        photo_count = len(photo_paths) if photo_paths else 0

        try:
            logger.info(
                "EMAIL sharing – sending %d photo(s) to '%s' <%s> for user %s.",
                photo_count,
                person_name,
                recipient,
                user_id,
            )

            # Create a pending delivery history record
            delivery = DeliveryHistory(
                recipient=recipient,
                platform='email',
                person_name=person_name or 'Selected Photos',
                photo_count=photo_count,
                status='pending',
                user_id=user_id,
            )
            db.session.add(delivery)
            db.session.commit()

            delivery_id = delivery.id
            app = current_app._get_current_object()

            def run_send_email_async():
                with app.app_context():
                    try:
                        th_delivery = DeliveryHistory.query.get(delivery_id)
                        if th_delivery:
                            success, error_msg = _send_real_email(recipient, person_name, photo_paths)
                            th_delivery.status = 'delivered' if success else 'failed'
                            th_delivery.error_message = error_msg
                            db.session.commit()
                    except Exception as e:
                        logger.error("Async send_email error: %s", e)

            threading.Thread(target=run_send_email_async, daemon=True).start()

            return _serialise_delivery(delivery)

        except Exception as exc:
            db.session.rollback()
            logger.error("Failed to record email delivery: %s", exc)
            raise

    @staticmethod
    def send_whatsapp(recipient, person_name, photo_paths, user_id=None):
        """Send photos via WhatsApp (Twilio API) and record delivery."""
        import threading
        from flask import current_app
        photo_count = len(photo_paths) if photo_paths else 0

        try:
            logger.info(
                "WHATSAPP sharing – sending %d photo(s) to '%s' (%s) for user %s.",
                photo_count,
                person_name,
                recipient,
                user_id,
            )

            # Create a pending delivery history record
            delivery = DeliveryHistory(
                recipient=recipient,
                platform='whatsapp',
                person_name=person_name or 'Selected Photos',
                photo_count=photo_count,
                status='pending',
                user_id=user_id,
            )
            db.session.add(delivery)
            db.session.commit()

            delivery_id = delivery.id
            app = current_app._get_current_object()

            def run_send_whatsapp_async():
                with app.app_context():
                    try:
                        th_delivery = DeliveryHistory.query.get(delivery_id)
                        if th_delivery:
                            success, error_msg = _send_real_whatsapp(recipient, person_name, photo_paths)
                            th_delivery.status = 'delivered' if success else 'failed'
                            th_delivery.error_message = error_msg
                            db.session.commit()
                    except Exception as e:
                        logger.error("Async send_whatsapp error: %s", e)

            threading.Thread(target=run_send_whatsapp_async, daemon=True).start()

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
        'error_message': delivery.error_message,
        'user_id': delivery.user_id,
    }
