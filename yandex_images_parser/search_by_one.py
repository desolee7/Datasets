import os
import time
import random
import requests
import json
import urllib.parse
from tqdm import tqdm
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from PIL import Image
import base64

class YandexImageSearcher:
    def __init__(self, headless=False):
        self.headless = headless
        self.driver = None
        
    def __init_driver(self):
        options = webdriver.FirefoxOptions()
        
        if self.headless:
            options.add_argument('--headless')
        
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("dom.push.enabled", False)
        options.set_preference("geo.enabled", False)
        options.set_preference("intl.accept_languages", "ru-RU, ru")
        options.set_preference("general.useragent.override", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0")
        options.add_argument("--width=1920")
        options.add_argument("--height=1080")
        
        if os.name == 'nt':
            geckodriver_path = "geckodriver/geckodriver.exe"
            if os.path.exists(geckodriver_path):
                service = Service(executable_path=geckodriver_path)
                self.driver = webdriver.Firefox(service=service, options=options)
            else:
                self.driver = webdriver.Firefox(options=options)
        else:
            self.driver = webdriver.Firefox(options=options)
        
        self.driver.implicitly_wait(10)
    
    def search_similar_by_file(self, image_path, limit=30):
        if not os.path.exists(image_path):
            print(f"Файл не найден: {image_path}")
            return []
        
        if not self.driver:
            self.__init_driver()
        
        try:
            self.driver.delete_all_cookies()
            
            with open(image_path, 'rb') as img_file:
                img_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = 'image/png' if ext == '.png' else 'image/jpeg'
            data_url = f"data:{mime_type};base64,{img_data}"
            
            self.driver.get("https://yandex.ru/images/")
            time.sleep(3)
            
            js_code = """
            const img = new Image();
            img.src = arguments[0];
            
            img.onload = function() {
                const canvas = document.createElement('canvas');
                canvas.width = img.width;
                canvas.height = img.height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);
                
                canvas.toBlob(function(blob) {
                    const file = new File([blob], 'image.png', {type: 'image/png'});
                    const fileInput = document.querySelector('input[type="file"]');
                    
                    if (fileInput) {
                        const dt = new DataTransfer();
                        dt.items.add(file);
                        fileInput.files = dt.files;
                        fileInput.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                }, 'image/png');
            };
            """
            
            self.driver.execute_script(js_code, data_url)
            time.sleep(8)
            
            similar_urls = self._extract_image_urls_enhanced(limit)
            return similar_urls
            
        except Exception as e:
            print(f"Ошибка при поиске: {e}")
            return []
    
    def _extract_image_urls_enhanced(self, limit):
        all_urls = []
        scroll_attempts = 0
        max_scrolls = 30
        
        while len(all_urls) < limit and scroll_attempts < max_scrolls:
            new_urls = self.driver.execute_script("""
                const urls = [];
                
                const serpItems = document.querySelectorAll('div.SerpItem, div[class*="serp-item"]');
                
                serpItems.forEach(item => {
                    try {
                        if (item.querySelector('[data-ad]') || 
                            item.className.includes('ad') || 
                            item.className.includes('adv')) {
                            return;
                        }
                        
                        const coverLink = item.querySelector('a.ImagesContentImage-Cover, a[class*="ImagesContentImage-Cover"]');
                        if (coverLink) {
                            const href = coverLink.getAttribute('href');
                            if (href) {
                                const urlParams = new URLSearchParams(href.split('?')[1]);
                                const imgUrl = urlParams.get('img_url');
                                if (imgUrl && !urls.includes(imgUrl)) {
                                    urls.push(decodeURIComponent(imgUrl));
                                }
                            }
                        }
                        
                        const bemData = item.getAttribute('data-bem');
                        if (bemData) {
                            try {
                                const data = JSON.parse(bemData);
                                if (data['serp-item'] && data['serp-item']['img_href']) {
                                    const imgUrl = data['serp-item']['img_href'];
                                    if (!urls.includes(imgUrl)) {
                                        urls.push(imgUrl);
                                    }
                                }
                            } catch(e) {}
                        }
                        
                        const allLinks = item.querySelectorAll('a[href*="img_url="]');
                        allLinks.forEach(link => {
                            const href = link.getAttribute('href');
                            const match = href.match(/img_url=([^&]+)/);
                            if (match) {
                                const imgUrl = decodeURIComponent(match[1]);
                                if (!urls.includes(imgUrl)) {
                                    urls.push(imgUrl);
                                }
                            }
                        });
                        
                    } catch(e) {}
                });
                
                if (urls.length === 0) {
                    document.querySelectorAll('a[href*="img_url="]').forEach(a => {
                        const href = a.getAttribute('href');
                        const match = href.match(/img_url=([^&]+)/);
                        if (match) {
                            const imgUrl = decodeURIComponent(match[1]);
                            if (!urls.includes(imgUrl) && 
                                !imgUrl.includes('yastatic.net') &&
                                !imgUrl.includes('mc.yandex.ru')) {
                                urls.push(imgUrl);
                            }
                        }
                    });
                }
                
                return urls;
            """)
            
            if new_urls:
                for url in new_urls:
                    if url not in all_urls:
                        all_urls.append(url)
            
            print(f"Собрано {len(all_urls)}/{limit} URL")
            
            if len(all_urls) >= limit:
                break
            
            old_height = self.driver.execute_script("return document.body.scrollHeight")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == old_height:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
        
        filtered_urls = []
        for url in all_urls:
            if any(x in url.lower() for x in ['yastatic.net', 'mc.yandex.ru', 'favicon', 'logo']):
                continue
            if url.startswith('http') and len(url) > 20:
                filtered_urls.append(url)
        
        return filtered_urls[:limit]
    
    def download_and_convert(self, urls, output_folder, limit=None):
        os.makedirs(output_folder, exist_ok=True)
        
        if limit and limit < len(urls):
            urls = urls[:limit]
        
        downloaded = []
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://yandex.ru/',
            'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
        })
        
        for i, url in enumerate(tqdm(urls, desc="Скачивание")):
            try:
                response = session.get(url, timeout=30)
                if response.status_code != 200 or len(response.content) < 3000:
                    continue
                
                content_type = response.headers.get('content-type', '').lower()
                ext = 'jpg'
                if 'webp' in content_type:
                    ext = 'webp'
                elif 'png' in content_type:
                    ext = 'png'
                
                temp_path = os.path.join(output_folder, f"temp_{i+1:04d}.{ext}")
                
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                
                if os.path.getsize(temp_path) < 3000:
                    os.remove(temp_path)
                    continue
                
                final_path = os.path.join(output_folder, f"similar_{i+1:04d}.jpg")
                
                if ext in ['webp', 'png']:
                    try:
                        with Image.open(temp_path) as img:
                            if img.mode in ('RGBA', 'LA', 'P'):
                                background = Image.new('RGB', img.size, (255, 255, 255))
                                if img.mode == 'P':
                                    img = img.convert('RGBA')
                                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                                img = background
                            elif img.mode != 'RGB':
                                img = img.convert('RGB')
                            
                            img.save(final_path, 'JPEG', quality=95)
                        
                        if os.path.getsize(final_path) > 1000:
                            downloaded.append(final_path)
                            os.remove(temp_path)
                        else:
                            os.rename(temp_path, os.path.join(output_folder, f"similar_{i+1:04d}.{ext}"))
                            downloaded.append(os.path.join(output_folder, f"similar_{i+1:04d}.{ext}"))
                    except:
                        os.rename(temp_path, os.path.join(output_folder, f"similar_{i+1:04d}.{ext}"))
                        downloaded.append(os.path.join(output_folder, f"similar_{i+1:04d}.{ext}"))
                else:
                    os.rename(temp_path, final_path)
                    downloaded.append(final_path)
                
                time.sleep(random.uniform(0.3, 0.8))
                
            except Exception as e:
                continue
        
        return downloaded
    
    def process_image(self, image_path, output_folder, limit=30):
        print(f"Обработка: {os.path.basename(image_path)}")
        
        similar_urls = self.search_similar_by_file(image_path, limit)
        
        if not similar_urls:
            print("Похожие изображения не найдены")
            return []
        
        downloaded = self.download_and_convert(similar_urls, output_folder, limit)
        print(f"Скачано {len(downloaded)} изображений в {output_folder}")
        return downloaded
    
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


def batch_process_images(image_paths, output_base_folder="similar_results", limit=30, headless=False):
    for i, image_path in enumerate(image_paths, 1):
        if not os.path.exists(image_path):
            print(f"Файл не найден: {image_path}")
            continue
        
        image_name = os.path.splitext(os.path.basename(image_path))[0]
        output_folder = os.path.join(output_base_folder, image_name)
        
        searcher = YandexImageSearcher(headless=headless)
        searcher.process_image(image_path, output_folder, limit)
        searcher.close()
        
        if i < len(image_paths):
            wait_time = random.uniform(10, 20)
            print(f"Ожидание {wait_time:.1f} сек...")
            time.sleep(wait_time)


if __name__ == "__main__":
    my_images = [
        "first_images/1.png",
        "first_images/2.png",
        "first_images/3.png",
        "first_images/4.png",
        "first_images/5.png"
    ]
    
    existing_images = [img for img in my_images if os.path.exists(img)]
    
    if not existing_images:
        print("Не найдены изображения в папке 'first_images/'")
    else:
        print(f"Найдено {len(existing_images)} изображений")
        
        batch_process_images(
            image_paths=existing_images,
            output_base_folder="downloaded_similar",
            limit=50,
            headless=False
        )
        
        print("Обработка завершена")