import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set
from flight_scraper import FlightScraper
from simple_scraper import SimpleFlightScraper
from config import DATA_FILE, FOCUS_ON_NEW_FLIGHTS_ONLY, IGNORE_PRICE_CHANGES, MAX_FLIGHT_AGE_HOURS

class FlightMonitor:
    def __init__(self):
        self.data_file = DATA_FILE
        self.previous_flights = self.load_previous_flights()
        
    def load_previous_flights(self) -> Dict:
        """טעינת נתוני טיסות קודמים מקובץ"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logging.info(f"נטענו נתוני {len(data.get('flights', []))} טיסות קודמות")
                    return data
            except Exception as e:
                logging.error(f"שגיאה בטעינת נתונים קודמים: {e}")
        
        return {'flights': [], 'last_check': None}
    
    def save_flights_data(self, flights: List[Dict], new_flights: List[Dict]):
        """שמירת נתוני טיסות לקובץ"""
        data = {
            'flights': flights,
            'new_flights': new_flights,
            'last_check': datetime.now().isoformat(),
            'total_flights_found': len(flights),
            'new_flights_count': len(new_flights)
        }
        
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"נשמרו נתוני {len(flights)} טיסות לקובץ")
        except Exception as e:
            logging.error(f"שגיאה בשמירת נתונים: {e}")
    
    def create_flight_signature(self, flight: Dict) -> str:
        """יצירת חתימה ייחודית לטיסה על בסיס יעד ותאריכי יציאה"""
        destination = flight.get('destination', '')
        dates = flight.get('dates', [])
        
        # יצירת חתימה על בסיס יעד ותאריכים (לא מחיר כי הוא קבוע)
        dates_str = '_'.join(sorted(dates)) if dates else 'no_dates'
        return f"{destination}_{dates_str}_{hash(flight.get('full_text', ''))}"
    
    def find_new_flights(self, current_flights: List[Dict]) -> List[Dict]:
        """זיהוי טיסות חדשות - זה הפוקוס העיקרי של המערכת"""
        # יצירת סט של חתימות טיסות קודמות
        previous_signatures = set()
        for flight in self.previous_flights.get('flights', []):
            signature = self.create_flight_signature(flight)
            previous_signatures.add(signature)
        
        # חיפוש טיסות חדשות
        new_flights = []
        for flight in current_flights:
            signature = self.create_flight_signature(flight)
            if signature not in previous_signatures:
                new_flights.append(flight)
                logging.info(f"טיסה חדשה נמצאה: {flight['destination']} - {flight.get('dates', 'ללא תאריכים')}")
        
        return new_flights
    
    def find_price_changes(self, current_flights: List[Dict]) -> List[Dict]:
        """זיהוי שינויי מחירים - מושבת כי המחירים קבועים"""
        if IGNORE_PRICE_CHANGES:
            logging.info("מעקב שינויי מחירים מושבת (מחירים קבועים באתר)")
            return []
        
        # הקוד הישן נשאר כאן למקרה שיהיה צורך עתידי
        price_changes = []
        return price_changes
    
    def filter_relevant_flights(self, flights: List[Dict]) -> List[Dict]:
        """סינון טיסות רלוונטיות - מותאם לטיסות רגע אחרון"""
        relevant_flights = []
        
        for flight in flights:
            # בדיקה שיש יעד
            if not flight.get('destination'):
                continue
            
            # בדיקת תוקף (טיסות לימים הקרובים בלבד)
            scraped_at = flight.get('scraped_at')
            if scraped_at:
                try:
                    scraped_time = datetime.fromisoformat(scraped_at)
                    if datetime.now() - scraped_time > timedelta(hours=MAX_FLIGHT_AGE_HOURS):
                        continue
                except:
                    pass
            
            # סינון טיסות שכבר עברו או רק להיום
            dates = flight.get('dates', [])
            if dates:
                # ניסיון לפרסר תאריכים ולוודא שהם בטווח הרלוונטי
                is_valid_date_range = self.check_date_validity(dates)
                if not is_valid_date_range:
                    continue
            
            relevant_flights.append(flight)
        
        return relevant_flights
    
    def check_date_validity(self, dates: List[str]) -> bool:
        """בדיקה שהתאריכים נמצאים בטווח הרלוונטי לטיסות רגע אחרון"""
        import re
        try:
            today = datetime.now().date()
            max_date = today + timedelta(days=14)  # טיסות עד 14 ימים קדימה

            any_parsed = False
            for date_str in dates:
                # חילוץ תבניות dd/mm מתוך טקסט חופשי
                for token in re.findall(r'\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?', date_str):
                    parsed_date = self.parse_date(token)
                    if parsed_date:
                        any_parsed = True
                        if today <= parsed_date <= max_date:
                            return True

            # אם לא הצלחנו לפרסר אף תאריך, נשאיר את הטיסה
            return not any_parsed
        except:
            # אם לא ניתן לפרסר, נשאיר את הטיסה
            return True

    def parse_date(self, date_str: str) -> datetime.date:
        """ניסיון לפרסר תאריך מסטרינג"""
        try:
            # פורמטים נפוצים
            formats = [
                '%d/%m/%Y', '%d.%m.%Y', '%d-%m-%Y',
                '%d/%m/%y', '%d.%m.%y', '%d-%m-%y',
                '%d/%m', '%d.%m'
            ]

            for fmt in formats:
                try:
                    parsed = datetime.strptime(date_str.strip(), fmt)
                    if fmt in ('%d/%m', '%d.%m'):
                        parsed = parsed.replace(year=datetime.now().year)
                    return parsed.date()
                except:
                    continue

            return None
        except:
            return None
    
    def check_for_updates(self) -> Dict:
        """בדיקה עיקרית לעדכונים - מותאמת לטיסות רגע אחרון"""
        logging.info("מתחיל בדיקת עדכונים לטיסות רגע אחרון")

        scraper = FlightScraper()
        try:
            # סריקת טיסות נוכחיות
            current_flights = scraper.scrape_flights()

            # סינון טיסות רלוונטיות
            relevant_flights = self.filter_relevant_flights(current_flights)

            # זיהוי טיסות חדשות (הפוקוס העיקרי)
            new_flights = self.find_new_flights(relevant_flights)

            # שינויי מחירים (מושבת)
            price_changes = []
            if not IGNORE_PRICE_CHANGES:
                price_changes = self.find_price_changes(relevant_flights)

            # שמירת נתונים
            self.save_flights_data(relevant_flights, new_flights)

            # עדכון נתונים פנימיים
            self.previous_flights = {
                'flights': relevant_flights,
                'last_check': datetime.now().isoformat()
            }

            result = {
                'total_flights': len(relevant_flights),
                'new_flights': new_flights,
                'price_changes': price_changes,
                'check_time': datetime.now().isoformat(),
                'focus_message': 'התמקדות בטיסות חדשות לימים הקרובים' if FOCUS_ON_NEW_FLIGHTS_ONLY else ''
            }

            logging.info(f"בדיקה הושלמה: {len(relevant_flights)} טיסות, {len(new_flights)} חדשות")
            return result

        except Exception as e:
            logging.error(f"שגיאה בבדיקת עדכונים: {e}")
            return {
                'total_flights': 0,
                'new_flights': [],
                'price_changes': [],
                'error': str(e),
                'check_time': datetime.now().isoformat()
            }
        finally:
            if scraper:
                scraper.close()
    
    def get_statistics(self) -> Dict:
        """קבלת סטטיסטיקות"""
        stats = {
            'total_flights_tracked': len(self.previous_flights.get('flights', [])),
            'last_check': self.previous_flights.get('last_check'),
            'destinations_found': set(),
            'monitoring_focus': 'טיסות חדשות לימים הקרובים' if FOCUS_ON_NEW_FLIGHTS_ONLY else 'כל השינויים',
            'price_monitoring': 'מושבת (מחירים קבועים)' if IGNORE_PRICE_CHANGES else 'פעיל',
            'check_interval': 'כל שעה (מתאים לטיסות רגע אחרון)'
        }
        
        flights = self.previous_flights.get('flights', [])
        if flights:
            destinations = [f.get('destination') for f in flights if f.get('destination')]
            stats['destinations_found'] = set(destinations)
        
        return stats

def test_monitor():
    """פונקציה לבדיקת המוניטור המותאם"""
    monitor = FlightMonitor()
    
    # הצגת סטטיסטיקות נוכחיות
    stats = monitor.get_statistics()
    print("סטטיסטיקות מערכת ניטור טיסות רגע אחרון:")
    print("=" * 55)
    print(f"- טיסות במעקב: {stats['total_flights_tracked']}")
    print(f"- יעדים: {', '.join(stats['destinations_found']) if stats['destinations_found'] else 'אין'}")
    print(f"- פוקוס ניטור: {stats['monitoring_focus']}")
    print(f"- מעקב מחירים: {stats['price_monitoring']}")
    print(f"- תדירות בדיקה: {stats['check_interval']}")
    print(f"- בדיקה אחרונה: {stats['last_check']}")
    print("-" * 55)
    
    # בדיקת עדכונים
    result = monitor.check_for_updates()
    
    print(f"תוצאות בדיקה:")
    print(f"- סה\"כ טיסות: {result['total_flights']}")
    print(f"- טיסות חדשות: {len(result['new_flights'])}")
    print(f"- {result.get('focus_message', '')}")
    
    if result['new_flights']:
        print("\n🆕 טיסות חדשות שנמצאו:")
        for flight in result['new_flights']:
            dates_str = ', '.join(flight.get('dates', [])) if flight.get('dates') else 'ללא תאריכים'
            print(f"✈️ {flight['destination']} - {dates_str}")
    else:
        print("\n😴 לא נמצאו טיסות חדשות")

if __name__ == "__main__":
    test_monitor()