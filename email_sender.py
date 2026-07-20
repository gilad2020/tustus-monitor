import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import logging
from typing import List, Dict
from config import (
    EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, EMAIL_USERNAME, 
    EMAIL_PASSWORD, MAILING_LIST, TUSTUS_URL, IGNORE_PRICE_CHANGES
)

# הגדרת לוגים
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flight_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class EmailSender:
    def __init__(self):
        self.smtp_server = EMAIL_SMTP_SERVER
        self.smtp_port = EMAIL_SMTP_PORT
        self.username = EMAIL_USERNAME
        self.password = EMAIL_PASSWORD
        self.mailing_list = [email.strip() for email in MAILING_LIST if email.strip()]
        
        if not self.username or not self.password:
            logging.warning("לא הוגדרו נתוני מייל - שליחת מיילים לא תעבוד")
    
    def create_flights_html(self, flights: List[Dict], title: str) -> str:
        """יצירת HTML לטיסות חדשות - מותאם לטיסות רגע אחרון"""
        if not flights:
            return ""
        
        html = f"""
        <div style="margin: 20px 0;">
            <h2 style="color: #2c5aa0; border-bottom: 2px solid #2c5aa0; padding-bottom: 10px;">
                {title}
            </h2>
            <div style="display: grid; gap: 15px;">
        """
        
        for flight in flights:
            destination = flight.get('destination', 'לא זמין')
            price = flight.get('price', 'מחיר קבוע')
            dates = flight.get('dates', [])
            full_text = flight.get('full_text', '')[:200] + '...' if len(flight.get('full_text', '')) > 200 else flight.get('full_text', '')
            
            # עיצוב תאריכים
            if dates:
                dates_str = ', '.join(dates)
                dates_display = f"📅 תאריכי יציאה: {dates_str}"
            else:
                dates_display = "📅 תאריכים יפורסמו בקרוב"
            
            # עיצוב מחיר
            price_display = f"{price}₪" if isinstance(price, (int, float)) else "מחיר קבוע"
            
            html += f"""
                <div style="
                    border: 1px solid #ddd; 
                    border-radius: 8px; 
                    padding: 15px; 
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <h3 style="color: #495057; margin: 0; font-size: 18px;">
                            ✈️ {destination}
                        </h3>
                        <span style="
                            background: #28a745; 
                            color: white; 
                            padding: 5px 15px; 
                            border-radius: 20px; 
                            font-weight: bold;
                            font-size: 16px;
                        ">
                            🆕 חדש!
                        </span>
                    </div>
                    <div style="color: #6c757d; margin-bottom: 8px;">
                        {dates_display}
                    </div>
                    <div style="color: #6c757d; margin-bottom: 8px;">
                        💰 מחיר: {price_display}
                    </div>
                    <div style="color: #6c757d; font-size: 14px; line-height: 1.4;">
                        {full_text}
                    </div>
                </div>
            """
        
        html += "</div></div>"
        return html
    
    def create_email_html(self, new_flights: List[Dict], price_changes: List[Dict], stats: Dict) -> str:
        """יצירת תבנית HTML למייל - מותאמת לטיסות רגע אחרון"""
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        # התחלת HTML
        html = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="he">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>טיסות רגע אחרון חדשות</title>
        </head>
        <body style="
            font-family: Arial, Helvetica, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background-color: #f8f9fa;
            direction: rtl;
        ">
            <div style="
                max-width: 800px; 
                margin: 0 auto; 
                background: white; 
                border-radius: 10px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                overflow: hidden;
            ">
                <!-- Header -->
                <div style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; 
                    padding: 30px 20px; 
                    text-align: center;
                ">
                    <h1 style="margin: 0; font-size: 28px;">
                        ✈️ טיסות רגע אחרון חדשות!
                    </h1>
                    <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">
                        TusTus - {current_time}
                    </p>
                </div>
                
                <!-- Content -->
                <div style="padding: 30px;">
        """
        
        # סיכום מהיר
        summary = f"""
                    <div style="
                        background: #e3f2fd; 
                        border-left: 4px solid #2196f3; 
                        padding: 20px; 
                        margin-bottom: 25px;
                        border-radius: 0 8px 8px 0;
                    ">
                        <h3 style="color: #1976d2; margin: 0 0 10px 0;">🚨 התראה חדשה!</h3>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                            <div style="text-align: center;">
                                <div style="font-size: 32px; font-weight: bold; color: #2196f3;">
                                    {len(new_flights)}
                                </div>
                                <div style="color: #666; font-size: 16px;">טיסות רגע אחרון חדשות</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 24px; font-weight: bold; color: #4caf50;">
                                    {stats.get('total_flights_tracked', 0)}
                                </div>
                                <div style="color: #666; font-size: 14px;">סה"כ טיסות במעקב</div>
                            </div>
                        </div>
                        <div style="margin-top: 15px; padding: 10px; background: #fff3cd; border-radius: 5px;">
                            <div style="color: #856404; font-weight: bold;">⚡ טיסות רגע אחרון - מחירים קבועים</div>
                            <div style="color: #856404; font-size: 14px;">המערכת מתמקדת בזיהוי טיסות חדשות לימים הקרובים</div>
                        </div>
                    </div>
        """
        
        html += summary
        
        # הוספת טיסות חדשות
        if new_flights:
            html += self.create_flights_html(new_flights, "🆕 טיסות רגע אחרון שנוספו")
        
        # אם אין עדכונים
        if not new_flights:
            html += """
                    <div style="
                        text-align: center; 
                        padding: 40px; 
                        color: #6c757d;
                        background: #f8f9fa;
                        border-radius: 8px;
                        margin: 20px 0;
                    ">
                        <div style="font-size: 48px; margin-bottom: 15px;">😴</div>
                        <h3 style="color: #495057;">אין טיסות חדשות</h3>
                        <p>לא נמצאו טיסות רגע אחרון חדשות מהבדיקה האחרונה.</p>
                    </div>
            """
        
        # Footer
        html += f"""
                    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                    
                    <div style="text-align: center; color: #6c757d; font-size: 14px;">
                        <p>
                            <a href="{TUSTUS_URL}" style="
                                color: #667eea; 
                                text-decoration: none; 
                                font-weight: bold;
                            ">🌐 עבור לאתר TusTus</a>
                        </p>
                        <p style="margin: 10px 0;">
                            💡 <strong>טיפ:</strong> טיסות רגע אחרון משתנות מהר - מומלץ לבדוק מיד!
                        </p>
                        <p style="margin: 5px 0;">
                            המערכת בודקה טיסות חדשות כל שעה
                        </p>
                        <p style="margin: 5px 0; font-size: 12px;">
                            מערכת ניטור טיסות רגע אחרון אוטומטית
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send_update_email(self, new_flights: List[Dict], price_changes: List[Dict], stats: Dict) -> bool:
        """שליחת מייל עדכון - מותאם לטיסות רגע אחרון"""
        if not self.mailing_list:
            logging.warning("רשימת תפוצה ריקה")
            return False
        
        if not self.username or not self.password:
            logging.error("נתוני מייל לא הוגדרו")
            return False
        
        try:
            # קביעת נושא המייל - התמקדות בטיסות חדשות
            if new_flights:
                if len(new_flights) == 1:
                    dest = new_flights[0].get('destination', 'יעד לא ידוע')
                    subject = f"🆕 טיסת רגע אחרון חדשה ל{dest}!"
                else:
                    subject = f"🆕 {len(new_flights)} טיסות רגע אחרון חדשות!"
            else:
                # אם אין טיסות חדשות, לא שולחים מייל
                logging.info("אין טיסות חדשות לשליחה")
                return True
            
            # יצירת HTML
            html_content = self.create_email_html(new_flights, price_changes, stats)
            
            # הגדרת המייל
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.username
            msg['To'] = ', '.join(self.mailing_list)
            
            # הוספת תוכן HTML
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # שליחת המייל
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logging.info(f"מייל נשלח בהצלחה ל-{len(self.mailing_list)} נמענים")
            return True
            
        except Exception as e:
            logging.error(f"שגיאה בשליחת מייל: {e}")
            return False
    
    def test_email(self) -> bool:
        """שליחת מייל בדיקה - מותאם לטיסות רגע אחרון"""
        test_flights = [
            {
                'destination': 'ברלין',
                'price': 'מחיר קבוע',
                'dates': ['15/08/2024', '16/08/2024'],
                'full_text': 'טיסת רגע אחרון לברלין! מקומות אחרונים זמינים לימים הקרובים.',
                'scraped_at': datetime.now().isoformat()
            },
            {
                'destination': 'פריז',
                'price': 'מחיר קבוע',
                'dates': ['17/08/2024'],
                'full_text': 'הזדמנות אחרונה לטיסה לפריז! יציאה מחר.',
                'scraped_at': datetime.now().isoformat()
            }
        ]
        
        test_stats = {
            'total_flights_tracked': 12,
            'last_check': datetime.now().isoformat()
        }
        
        return self.send_update_email(test_flights, [], test_stats)

def test_email_sender():
    """פונקציה לבדיקת שליחת מייל - מותאמת לטיסות רגע אחרון"""
    sender = EmailSender()
    
    print(f"רשימת תפוצה: {sender.mailing_list}")
    print(f"שרת מייל: {sender.smtp_server}:{sender.smtp_port}")
    
    if sender.username and sender.password:
        print("שולח מייל בדיקה לטיסות רגע אחרון...")
        success = sender.test_email()
        if success:
            print("✅ מייל בדיקה נשלח בהצלחה!")
        else:
            print("❌ שגיאה בשליחת מייל")
    else:
        print("❌ נתוני מייל לא הוגדרו - לא ניתן לשלוח מייל")

if __name__ == "__main__":
    test_email_sender()