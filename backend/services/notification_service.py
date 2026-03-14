import logging

logger = logging.getLogger(__name__)

def notify_responder(responder_id: str, mission_id: str, message: str = ""):
    """
    Simulates sending a notification (Push/SMS) to the responder's app.
    In a real system, this would call FCM, Twilio, or AWS SNS.
    """
    
    # Mock Notification Logic
    logger.info(f"🔔 [NOTIFICATION] Sending alert to Responder {responder_id}")
    logger.info(f"   Mission: {mission_id}")
    logger.info(f"   App Message: '{message}' if provided")
    
    return {
        "status": "success",
        "delivered_to": responder_id,
        "channel": "push_notification"
    }

def notify_sos_creator(sos_id: str, message: str):
    """
    Simulates sending an SMS back to the person who requested SOS to inform them help is on the way.
    """
    logger.info(f"📱 [SMS OUT] To SOS {sos_id} Creator: {message}")
    
    return {
        "status": "success",
        "delivered_to": sos_id,
        "channel": "sms"
    }
