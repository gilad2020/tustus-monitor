import os
from dotenv import load_dotenv

load_dotenv()

# הגדרות מייל
EMAIL_SMTP_SERVER = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
EMAIL_SMTP_PORT = int(os.getenv('EMAIL_SMTP_PORT', '587'))
EMAIL_USERNAME = os.getenv('EMAIL_USERNAME')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

# רשימת תפוצה
MAILING_LIST = os.getenv('MAILING_LIST', '').split(',')

# הגדרות סריקה
TUSTUS_URL = 'https://www.tustus.co.il/Arkia/Home'
CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', '60'))  # שעה במקום חצי שעה

# יעדים מועדפים - ניתן להוסיף או לשנות
PREFERRED_DESTINATIONS = []  # ריק = כל היעדים

# רשימת יעדים לא רלוונטיים (יוצאים מההתראה)
EXCLUDED_DESTINATIONS = [d.strip() for d in os.getenv('EXCLUDED_DESTINATIONS', '').split(',') if d.strip()]

# הגדרות נוספות
DATA_FILE = 'flights_data.json'
LOG_FILE = 'flight_monitor.log'

# הגדרות ספציפיות לאתר TusTus
# מאחר שהמחירים קבועים והטיסות לימים הקרובים
FOCUS_ON_NEW_FLIGHTS_ONLY = True  # התמקד רק בטיסות חדשות
IGNORE_PRICE_CHANGES = True  # התעלם משינויי מחירים
MAX_FLIGHT_AGE_HOURS = 72  # טיסות רק עד 3 ימים
MIN_DAYS_ADVANCE = 1  # טיסות החל ממחר