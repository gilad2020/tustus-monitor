import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import logging
from datetime import datetime
from config import TUSTUS_URL, PREFERRED_DESTINATIONS, EXCLUDED_DESTINATIONS

# הגדרת לוגים
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flight_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class FlightScraper:
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """הגדרת WebDriver עם Chrome"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            mac_chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            chrome_bin = os.getenv('CHROME_BIN') or (mac_chrome if os.path.exists(mac_chrome) else None)
            if chrome_bin:
                chrome_options.binary_location = chrome_bin

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            # Post-init stealth tweak
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logging.info("WebDriver הוגדר בהצלחה")
        except Exception as e:
            logging.error(f"שגיאה בהגדרת WebDriver: {e}")
            raise
    
    def scrape_flights(self):
        """סריקת טיסות מהאתר"""
        try:
            logging.info(f"מתחיל סריקה של {TUSTUS_URL}")
            self.driver.get(TUSTUS_URL)
            
            # המתנה לטעינת הדף
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # המתנה לטעינת התוכן הדינמי (אלמנטי הטיסות עצמם), עם timeout סביר
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".show_item"))
                )
            except Exception:
                # אם אחרי ה-timeout עדיין אין אלמנטים, כנראה שבאמת אין טיסות כרגע
                pass

            # חיפוש אלמנטים של טיסות
            flights = []
            
            # ניסיון לזהות טיסות על פי מבנים נפוצים
            flight_elements = self.find_flight_elements()
            
            for element in flight_elements:
                flight_data = self.extract_flight_data(element)
                if flight_data and self.is_relevant_destination(flight_data.get('destination', '')):
                    flights.append(flight_data)
            
            logging.info(f"נמצאו {len(flights)} טיסות רלוונטיות")
            return flights
            
        except Exception as e:
            logging.error(f"שגיאה בסריקת טיסות: {e}")
            return []
    
    def find_flight_elements(self):
        """חיפוש אלמנטים של טיסות בדף"""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, ".show_item")
            if elements:
                logging.info(f"נמצאו {len(elements)} אלמנטים עם סלקטור .show_item")
                return elements
        except:
            pass
        logging.warning("לא נמצאו אלמנטים של טיסות")
        return []

    def extract_flight_data(self, element):
        """חילוץ נתונים מאלמנט טיסה"""
        import re
        try:
            # יעד מתוך תכונת con_desc
            destination = element.get_attribute('con_desc') or ''
            destination = destination.split(' - ')[0].strip()

            if not destination:
                return None

            # דילוג על יעדים מוחרגים
            if any(destination == ex for ex in EXCLUDED_DESTINATIONS):
                return None

            # סינון לפי יעדים מועדפים
            if PREFERRED_DESTINATIONS and destination not in PREFERRED_DESTINATIONS:
                return None

            # מחיר מתוך תכונת data_number_ga_price
            price_attr = element.get_attribute('data_number_ga_price') or ''
            price = int(price_attr) if price_attr.isdigit() else None

            # מטבע מתוך data_ga_currency
            currency = element.get_attribute('data_ga_currency') or '₪'

            # תאריכים מתוך data_ga_item_brand (פורמט: "חזרה-יציאה")
            brand = element.get_attribute('data_ga_item_brand') or ''
            brand_parts = [d.strip() for d in brand.split('-') if d.strip()] if brand else []
            # הפורמט הוא return-departure, הופכים לסדר הנכון: [יציאה, חזרה]
            brand_dates = [brand_parts[1], brand_parts[0]] if len(brand_parts) == 2 else None

            if destination and price:
                return {
                    'destination': destination,
                    'price': price,
                    'currency': currency,
                    'dates': brand_dates,
                    'scraped_at': datetime.now().isoformat(),
                    'url': TUSTUS_URL
                }
        except Exception as e:
            logging.warning(f"שגיאה בחילוץ נתונים מאלמנט: {e}")

        return None
    
    def is_relevant_destination(self, destination):
        if not destination:
            return False
        if any(destination == ex for ex in EXCLUDED_DESTINATIONS):
            return False
        if not PREFERRED_DESTINATIONS:
            return True
        return destination in PREFERRED_DESTINATIONS
    
    def close(self):
        """סגירת WebDriver"""
        if self.driver:
            self.driver.quit()
            logging.info("WebDriver נסגר")

def test_scraper():
    """פונקציה לבדיקת הסקרפר"""
    scraper = FlightScraper()
    try:
        flights = scraper.scrape_flights()
        print(f"נמצאו {len(flights)} טיסות:")
        for flight in flights:
            currency = flight.get('currency', '₪')
            print(f"- {flight['destination']}: {flight['price']}{currency}")
            print(f"  תאריכים: {flight['dates']}")
            print("-" * 50)
    finally:
        scraper.close()

if __name__ == "__main__":
    test_scraper()