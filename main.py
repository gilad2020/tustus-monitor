#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import schedule
import time
import logging
import signal
import sys
from datetime import datetime
from flight_monitor import FlightMonitor
from email_sender import EmailSender
from config import CHECK_INTERVAL_MINUTES, FOCUS_ON_NEW_FLIGHTS_ONLY, IGNORE_PRICE_CHANGES

# הגדרת לוגים
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flight_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class FlightAlertSystem:
    def __init__(self):
        self.monitor = FlightMonitor()
        self.email_sender = EmailSender()
        self.running = True
        
        # הגדרת טיפול בסיגנלים לסיום נקי
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """טיפול בסיגנל סיום"""
        logging.info(f"התקבל סיגנל {signum}, מתחיל סיום נקי...")
        self.running = False
    
    def check_and_notify(self):
        """פונקציה עיקרית לבדיקה ושליחת התראות - מותאמת לטיסות רגע אחרון"""
        try:
            logging.info("מתחיל בדיקת טיסות רגע אחרון...")
            
            # בדיקת עדכונים
            result = self.monitor.check_for_updates()
            
            if 'error' in result:
                logging.error(f"שגיאה בבדיקת טיסות: {result['error']}")
                return
            
            new_flights = result.get('new_flights', [])
            price_changes = result.get('price_changes', [])

            if new_flights:
                logging.info(f"נמצאו {len(new_flights)} טיסות רגע אחרון חדשות")
            else:
                logging.info("לא נמצאו טיסות רגע אחרון חדשות")

            # קבלת סטטיסטיקות
            stats = self.monitor.get_statistics()

            # שליחת מייל - תמיד, גם ללא טיסות חדשות, כדי לראות שהריצה קרתה
            success = self.email_sender.send_update_email(new_flights, price_changes, stats)

            if success:
                logging.info("מייל עדכון נשלח בהצלחה")
            else:
                logging.error("שגיאה בשליחת מייל עדכון")
                
        except Exception as e:
            logging.error(f"שגיאה כללית בבדיקת טיסות: {e}")
    
    def run_once(self):
        """הרצה חד-פעמית"""
        logging.info("מריץ בדיקה חד-פעמית לטיסות רגע אחרון...")
        self.check_and_notify()
        logging.info("בדיקה חד-פעמית הושלמה")
    
    def run_continuous(self):
        """הרצה רציפה עם שדולר - מותאמת לטיסות רגע אחרון"""
        logging.info(f"מתחיל ניטור רציף לטיסות רגע אחרון - בדיקה כל {CHECK_INTERVAL_MINUTES} דקות")
        
        if FOCUS_ON_NEW_FLIGHTS_ONLY:
            logging.info("מצב ניטור: התמקדות בטיסות חדשות בלבד")
        
        if IGNORE_PRICE_CHANGES:
            logging.info("מצב מחירים: מעקב שינויי מחירים מושבת (מחירים קבועים)")
        
        # הגדרת תזמון
        schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(self.check_and_notify)
        
        # הרצת בדיקה ראשונית
        logging.info("מריץ בדיקה ראשונית...")
        self.check_and_notify()
        
        # לולאה עיקרית
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(30)  # בדיקה כל 30 שניות אם יש משימות ממתינות
            except KeyboardInterrupt:
                logging.info("התקבל Ctrl+C, יוצא...")
                break
            except Exception as e:
                logging.error(f"שגיאה בלולאה העיקרית: {e}")
                time.sleep(60)  # המתנה דקה לפני המשך
        
        logging.info("מערכת ניטור טיסות רגע אחרון נסגרה")
    
    def show_status(self):
        """הצגת סטטוס המערכת - מותאם לטיסות רגע אחרון"""
        try:
            stats = self.monitor.get_statistics()
            
            print("=" * 70)
            print("🛫 סטטוס מערכת ניטור טיסות רגע אחרון TusTus")
            print("=" * 70)
            
            print(f"📊 טיסות במעקב: {stats['total_flights_tracked']}")
            print(f"🎯 יעדים נמצאים: {len(stats['destinations_found'])}")
            if stats['destinations_found']:
                print(f"   {', '.join(sorted(stats['destinations_found']))}")
            
            print(f"🔍 פוקוס ניטור: {stats.get('monitoring_focus', 'כל השינויים')}")
            print(f"💰 מעקב מחירים: {stats.get('price_monitoring', 'פעיל')}")
            print(f"⏱️  תדירות בדיקה: {stats.get('check_interval', f'כל {CHECK_INTERVAL_MINUTES} דקות')}")
            
            print(f"🕒 בדיקה אחרונה: {stats['last_check'] or 'טרם בוצעה'}")
            
            print(f"📧 רשימת תפוצה: {len(self.email_sender.mailing_list)} נמענים")
            if self.email_sender.mailing_list:
                for email in self.email_sender.mailing_list:
                    print(f"   • {email}")
            
            print("=" * 70)
            print("💡 טיפים:")
            print("   • המערכת מתמקדת בטיסות רגע אחרון לימים הקרובים")
            print("   • מחירים קבועים - ההתמקדות בטיסות חדשות בלבד")
            print("   • טיסות רגע אחרון משתנות מהר - בדוק מיד כשמגיע מייל!")
            print("=" * 70)
            
        except Exception as e:
            logging.error(f"שגיאה בהצגת סטטוס: {e}")

def main():
    """פונקציה עיקרית"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='מערכת ניטור והתראות לטיסות רגע אחרון TusTus',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
דוגמאות שימוש:
  python main.py --run-once          # הרצה חד-פעמית
  python main.py --continuous        # הרצה רציפה (ברירת מחדל)
  python main.py --status            # הצגת סטטוס
  python main.py --test-email        # בדיקת מייל

מאפיינים:
• התמקדות בטיסות רגע אחרון חדשות
• מחירים קבועים (ללא מעקב שינויי מחירים)
• בדיקה כל שעה (מתאים לטיסות רגע אחרון)
        """
    )
    
    parser.add_argument('--run-once', action='store_true', 
                       help='הרצה חד-פעמית של בדיקת טיסות')
    parser.add_argument('--continuous', action='store_true', 
                       help='הרצה רציפה עם שדולר (ברירת מחדל)')
    parser.add_argument('--status', action='store_true',
                       help='הצגת סטטוס המערכת')
    parser.add_argument('--test-email', action='store_true',
                       help='שליחת מייל בדיקה')
    
    args = parser.parse_args()
    
    # יצירת מערכת ההתראות
    alert_system = FlightAlertSystem()
    
    try:
        if args.status:
            alert_system.show_status()
        elif args.test_email:
            print("שולח מייל בדיקה לטיסות רגע אחרון...")
            success = alert_system.email_sender.test_email()
            if success:
                print("✅ מייל בדיקה נשלח בהצלחה!")
            else:
                print("❌ שגיאה בשליחת מייל בדיקה")
        elif args.run_once:
            alert_system.run_once()
        else:
            # ברירת מחדל - הרצה רציפה
            alert_system.run_continuous()
            
    except KeyboardInterrupt:
        logging.info("המערכת נסגרה על ידי המשתמש")
    except Exception as e:
        logging.error(f"שגיאה כללית: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()