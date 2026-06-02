import os
import sys
import glob
import time
import json
import urllib
import random
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
from selenium import webdriver
from fake_headers import Headers
from requests import PreparedRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.common.exceptions import SessionNotCreatedException
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotInteractableException

# Добавьте этот импорт
try:
    from fake_useragent import UserAgent
    FAKE_UA_AVAILABLE = True
except ImportError:
    FAKE_UA_AVAILABLE = False
    print("Для лучшей маскировки установите: pip install fake-useragent")


class Size:
    def __init__(self):
        self.large = "large"
        self.medium = "medium"
        self.small = "small"


class Orientation:
    def __init__(self):
        self.horizontal = "horizontal"
        self.vertical = "vertical"
        self.square = "square"


class ImageType:
    def __init__(self):
        self.photo = "photo"
        self.clipart = "clipart"
        self.lineart = "lineart"
        self.face = "face"
        self.demotivator = "demotivator"


class Color:
    def __init__(self):
        self.color = "color"
        self.gray = "gray"
        self.red = "red"
        self.orange = "orange"
        self.yellow = "yellow"
        self.cyan = "cyan"
        self.green = "green"
        self.blue = "blue"
        self.violet = "violet"
        self.white = "white"
        self.black = "black"


class Format:
    def __init__(self):
        self.jpg = "jpg"
        self.png = "png"
        self.gif = "gifan"


class Parser:
    def __init__(self, headless=False, firefox_profile_path=None):

        if not firefox_profile_path:
            firefox_profile_path = self.__find_firefox_profile()

        self.size = Size()
        self.orientation = Orientation()
        self.type = ImageType()
        self.color = Color()
        self.format = Format()
        self.headless = headless
        self.profile_path = firefox_profile_path

    def query_search(self,
                     query: str,
                     limit: int = 100,
                     delay: float = 6.0,
                     size: Size = None,
                     orientation: Orientation = None,
                     image_type: ImageType = None,
                     color: Color = None,
                     image_format: Format = None,
                     site: str = None) -> list:

        params = {"text": query,
                  "isize": size,
                  "iorient": orientation,
                  "type": image_type,
                  "icolor": color,
                  "itype": image_format,
                  "site": site,
                  "nomisspell": 1,
                  "noreask": 1,
                  "p": 0}

        return self.__get_images(params=params, limit=limit, delay=delay)

    def image_search(self,
                     url: str,
                     limit: int = 100,
                     delay: float = 6.0,
                     size: Size = None,
                     orientation: Orientation = None,
                     color: Color = None,
                     image_format: Format = None,
                     site: str = None) -> list:

        params = {"url": url,
                  "isize": size,
                  "iorient": orientation,
                  "icolor": color,
                  "itype": image_format,
                  "site": site,
                  "rpt": "imageview",
                  "cbir_page": "similar",
                  "p": 0}

        return self.__get_images(params=params, limit=limit, delay=delay)

    def __random_delay(self, base_delay, variation=2):
        """Случайная задержка как у человека"""
        delay = base_delay + random.uniform(-variation, variation)
        return max(0.5, delay)

    def __random_mouse_movement(self, driver):
        """Имитирует случайное движение мыши"""
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(driver)
            for _ in range(random.randint(1, 3)):
                actions.move_by_offset(random.randint(-200, 200), random.randint(-100, 100))
                actions.perform()
                time.sleep(random.uniform(0.1, 0.3))
            # Возвращаем мышь в исходное положение
            actions.move_by_offset(random.randint(-50, 50), random.randint(-30, 30))
            actions.perform()
        except Exception:
            pass

    def __random_scroll(self, driver):
        """Случайная прокрутка страницы"""
        scroll_distance = random.randint(300, 800)
        driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
        time.sleep(random.uniform(0.5, 1.5))
        # Иногда прокручиваем назад
        if random.random() < 0.3:
            driver.execute_script(f"window.scrollBy(0, -{random.randint(100, 300)});")
            time.sleep(random.uniform(0.3, 0.8))

    def __get_user_agent(self):
        """Возвращает случайный User-Agent"""
        if FAKE_UA_AVAILABLE:
            ua = UserAgent()
            return ua.random
        else:
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:114.0) Gecko/20100101 Firefox/114.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:113.0) Gecko/20100101 Firefox/113.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            ]
            return random.choice(user_agents)

    def __get_images(self, params: dict, limit: int, delay: float) -> list:
        """Returns the specified number of direct URL to images"""

        request = self.__prepare_request(params)

        try:
            options = webdriver.FirefoxOptions()

            if self.headless:
                options.add_argument('--headless')

            # Отключаем WebDriver
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference("useAutomationExtension", False)
            
            # Отключаем геолокацию и уведомления
            options.set_preference("dom.push.enabled", False)
            options.set_preference("geo.enabled", False)
            options.set_preference("geo.provider.use_corelocation", False)
            options.set_preference("geo.wifi.uri", "")
            options.set_preference("permissions.default.geo", 2)
            
            # Язык и регион
            options.set_preference("intl.accept_languages", "ru-RU, ru")
            options.set_preference("general.useragent.locale", "ru-RU")
            
            # Отключаем телеметрию
            options.set_preference("fission.bfcacheInParent", False)
            options.set_preference("toolkit.telemetry.enabled", False)
            options.set_preference("datareporting.healthreport.uploadEnabled", False)
            
            # Случайный User-Agent
            options.set_preference("general.useragent.override", self.__get_user_agent())
            
            # Размер окна как у реального пользователя
            width = random.randint(1200, 1920)
            height = random.randint(800, 1080)
            options.add_argument(f"--width={width}")
            options.add_argument(f"--height={height}")

            if sys.platform.startswith('win'):
                geckodriver_path = "geckodriver/geckodriver.exe"
                service = Service(executable_path=geckodriver_path)
                driver = webdriver.Firefox(service=service, options=options)

            elif sys.platform.startswith('linux'):
                options.add_argument(f"--profile={self.profile_path}")

                geckodriver_paths = [
                    "/usr/bin/geckodriver",
                    "/usr/local/bin/geckodriver",
                    "/snap/bin/geckodriver",
                ]

                driver = None
                for geckodriver_path in geckodriver_paths:
                    try:
                        service = Service(executable_path=geckodriver_path)
                        driver = webdriver.Firefox(service=service, options=options)
                        break
                    except WebDriverException:
                        continue

                if driver is None:
                    raise WebDriverException("Could not find a valid geckodriver path")

            else:
                raise NotImplementedError("Your exotic operating system is not supported")

        except SessionNotCreatedException as e:
            print(f"Error: SessionNotCreatedException. FireFox may not be installed.\n\n{e.msg}")
            raise SystemExit(1)

        try:
            driver.get(request.url)
        except WebDriverException as e:
            print(f"Error: WebDriverException.\n\n{e.msg}")
            raise SystemExit(1)

        # Случайная задержка перед началом
        time.sleep(self.__random_delay(delay, 3))
        
        # Случайное движение мыши
        self.__random_mouse_movement(driver)
        
        pbar = tqdm(total=limit)

        while True:
            html = driver.page_source
            images = self.__parse_html(html)

            if len(images) == 0:
                pbar.set_postfix_str("Something went wrong... no images found.")
                break

            pbar.n = len(images) if len(images) <= limit else limit
            pbar.refresh()

            if len(images) >= limit:
                break
            else:
                old_page_height = driver.execute_script("return document.body.scrollHeight")
                
                # Случайная прокрутка вместо прямой
                self.__random_scroll(driver)
                
                # Случайное движение мыши
                self.__random_mouse_movement(driver)
                
                # Случайная задержка
                time.sleep(self.__random_delay(delay, 2))
                
                new_page_height = driver.execute_script("return document.body.scrollHeight")

                if old_page_height == new_page_height:
                    try:
                        # Пробуем нажать кнопку "Показать ещё"
                        driver.find_element(By.XPATH, "//div[starts-with(@class, 'FetchListButton')]//button[starts-with(@class, 'Button2')]").click()
                        self.__random_mouse_movement(driver)
                        time.sleep(self.__random_delay(delay, 1))
                    except NoSuchElementException:
                        break
                    except ElementNotInteractableException:
                        pbar.set_postfix_str("Fewer images found")
                        break
                    except Exception as e:
                        print(e)

        driver.close()
        driver.quit()

        return images[:limit]

    def __find_firefox_profile(self):
        profile_paths = [
            "~/snap/firefox/common/.mozilla/firefox/*.default*",
            "~/.mozilla/firefox/*.default*",
            "~/.var/app/org.mozilla.firefox/.mozilla/firefox/*.default*"
        ]

        for path in profile_paths:
            full_path = os.path.expanduser(path)
            profiles = glob.glob(full_path)
            if profiles:
                return profiles[0]

        return "Profile not found"

    def __prepare_request(self, params: dict) -> PreparedRequest:
        """Prepares a GET request to Yandex Images"""

        params = {k: v for k, v in params.items() if v is not None}
        headers = Headers(headers=True).generate()

        request = requests.Request(method="GET",
                                   url="https://yandex.ru/images/search",
                                   params=params,
                                   headers=headers).prepare()
        return request

    def __parse_html(self, html: str) -> list:
        """Extracts direct links to images from the html code"""

        soup = BeautifulSoup(html, "lxml")
        pictures_place = soup.find("div", {"class": "SerpList"})

        if pictures_place is not None:
            urls = []
            try:
                pictures = pictures_place.find_all("div", {"class": "SerpItem"})

                for pic in pictures:
                    url_soup = BeautifulSoup(str(pic), 'html.parser')
                    image_url = url_soup.find('a', class_='Link ImagesContentImage-Cover')['href']
                    image_url = urllib.parse.parse_qs(urllib.parse.urlparse(image_url).query)['img_url'][0]

                    urls.append(image_url)

                return urls
            except AttributeError:
                return urls

        else:
            pictures_place = soup.find("div", {"class": "cbir-page-layout__main-content"})
            urls = []
            try:
                pictures = pictures_place.find_all("div", {"class": "serp-item"})

                for pic in pictures:
                    data = json.loads(pic.get("data-bem"))
                    image = data['serp-item']['img_href']
                    urls.append(image)

                return urls
            except AttributeError:
                return urls