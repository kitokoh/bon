import os
import time
import json
import random
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

class WebScraping:
    def __init__(self, headless: bool = False, time_out: int = 0,
                 incognito: bool = False, start_openning: bool = True, width: int = 1280, height: int = 720,
                 mute: bool = True):
        self.basetime = 1
        self.current_folder = os.path.dirname(__file__)
        self.__headless__ = headless
        self.__user_data_dir__ = os.getenv("CHROME_FOLDER")
        self.__incognito__ = incognito
        self.__start_openning__ = start_openning
        self.__width__ = width
        self.__height__ = height
        self.__mute__ = mute
        self.__web_page__: Optional[str] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        if start_openning:
            self.__set_browser_instance__()

        if time_out > 0:
            self.page.set_default_timeout(time_out * 1000)

    def __set_browser_instance__(self):
        playwright = sync_playwright().start()
        browser_type = playwright.chromium
        browser_options = {
            "headless": self.__headless__,
            "args": [
                f"--window-size={self.__width__},{self.__height__}",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--mute-audio" if self.__mute__ else ""
            ]
        }

        # Utiliser launch_persistent_context pour spécifier user_data_dir
        self.context = browser_type.launch_persistent_context(
            self.__user_data_dir__,
            **browser_options
        )
        self.page = self.context.new_page()

    def set_cookies(self, cookies: List[Dict[str, Any]]):
        self.context.add_cookies(cookies)

    def screenshot(self, base_name: str):
        if not base_name.endswith(".png"):
            base_name += ".png"
        self.page.screenshot(path=base_name)

    def full_screenshot(self, path: str):
        self.page.screenshot(path=path, full_page=True)

    def get_browser(self) -> Browser:
        return self.context.browser

    def end_browser(self):
        self.context.close()
        self.page = None
        self.context = None

    def send_data(self, selector: str, data: str):
        self.page.fill(selector, data)

    def click_js(self, selectors: list):
        for selector in selectors:
            try:
                # Attendre que l'élément soit visible et interactif
                self.page.wait_for_selector(selector, state='visible', timeout=10000)
                self.page.click(selector)
                print(f"Clicked on element with selector: {selector}")
                return  # Sortir de la fonction si le clic est réussi
            except Exception as e:
                print(f"Failed to click on element with selector: {selector}. Error: {e}")
        print("All selectors failed. Could not click the element.")

    def wait_load(self, selector: str, time_out: int = 1):
        self.page.wait_for_selector(selector, timeout=time_out * 1000)

    def get_text(self, selector: str) -> Optional[str]:
        return self.page.text_content(selector)

    def get_texts(self, selector: str) -> List[str]:
        return self.page.eval_on_selector_all(selector, "elements => elements.map(e => e.textContent)")

    def set_page(self, web_page: str, time_out: int = 0):
        self.__web_page__ = web_page
        if time_out > 0:
            self.page.set_default_navigation_timeout(time_out * 1000)
        self.page.goto(web_page)

    def go_bottom(self, selector: str = "body"):
        self.page.evaluate(f"document.querySelector('{selector}').scrollIntoView(false)")

    def go_top(self, selector: str = "body"):
        self.page.evaluate(f"document.querySelector('{selector}').scrollIntoView(true)")

    def refresh_selenium(self, time_units: int = 1):
        self.page.reload()
        time.sleep(self.basetime * time_units)

    def save_page(self, file_html: str):
        content = self.page.content()
        with open(os.path.join(self.current_folder, file_html), "w", encoding='utf-8') as file:
            file.write(content)

    def zoom(self, percentage: int = 100):
        self.page.evaluate(f"document.body.style.zoom = '{percentage / 100}'")

    def kill(self):
        self.end_browser()

class Scraper(WebScraping):
    def __init__(self):
        current_folder = os.path.dirname(__file__)
        parent_folder = os.path.dirname(current_folder)
        self.data_path = os.path.join(parent_folder, "data.json")
        self.data_pathx = os.path.join(parent_folder, "data1.json")
        self.selectors_path = os.path.join(parent_folder, "config", "selectors.json")

        with open(self.data_path, encoding="UTF-8") as file:
            self.json_data = json.load(file)
        with open(self.data_pathx, encoding="UTF-8") as file:
            self.json_datax = json.load(file)
        with open(self.selectors_path, encoding="UTF-8") as file:
            self.selectors = json.load(file)

        super().__init__(start_openning=True)

    def post_in_groupsx(self):
        posts_done = []
        group = random.choice(self.json_datax["groups"])
        self.set_page(group)
        time.sleep(5)
        self.refresh_selenium()

        post_text = random.choice(self.json_datax["posts"])
        post_images = random.sample(self.json_datax["images"], min(30, len(self.json_datax["images"])))

        # Utiliser une liste de sélecteurs pour le bouton d'affichage de l'entrée
        display_input_selectors = self.selectors["display_input"]
        try:
            self.click_js(display_input_selectors)
        except Exception as e:
            print(f'Error opening text input: "{post_text}" ({group}) - {e}')
            return

        self.refresh_selenium()

        try:
            self.send_data(self.selectors["input"], post_text)
        except Exception as e:
            print(f'Error writing text: "{post_text}" ({group}) - {e}')
            return

        for image_path in post_images:
            absolute_image_path = self.get_absolute_path(image_path)
            self.click_js(self.selectors["show_image_input"])
            self.refresh_selenium()
            self.page.set_input_files(self.selectors["add_image"], absolute_image_path)

        self.refresh_selenium()
        try:
            self.click_js(self.selectors["submit"])
        except Exception as e:
            print(f'Error submitting post: "{post_text}" ({group}) - {e}')
            return

        print(f'Post successful: "{post_text}" ({group})')
        posts_done.append([group, post_text])
        time.sleep(int(os.getenv("WAIT_MIN")) * 60)

    def get_absolute_path(self, relative_path: str) -> str:
        current_folder = os.path.dirname(__file__)
        return os.path.join(current_folder, relative_path)

    def post_in_groups(self):
        posts_done = []
        for group in self.json_data["groups"]:
            self.set_page(group)
            time.sleep(5)
            self.refresh_selenium()

            post = random.choice(self.json_data["posts"])
            post_text = post["text"]
            post_image = post.get("image", "")

            try:
                self.click_js(self.selectors["display_input"])
            except Exception as e:
                print(f'Error opening text input: "{post_text}" ({group}) - {e}')
                continue

            self.refresh_selenium()

            try:
                self.send_data(self.selectors["input"], post_text)
            except Exception as e:
                print(f'Error writing text: "{post_text}" ({group}) - {e}')
                continue

            if post_image:
                absolute_image_path = self.get_absolute_path(post_image)
                self.click_js(self.selectors["show_image_input"])
                self.refresh_selenium()
                self.page.set_input_files(self.selectors["add_image"], absolute_image_path)

            self.refresh_selenium()
            try:
                self.click_js(self.selectors["submit"])
            except Exception as e:
                print(f'Error submitting post: "{post_text}" ({group}) - {e}')
                continue

            time.sleep(int(os.getenv("WAIT_MIN")) * 60)
            posts_done.append([group, post])
            print(f'Post successful: "{post_text}" ({group})')

    def save_groups(self, keyword: str):
        print("Searching groups...")
        search_page = f"https://www.facebook.com/groups/search/groups/?q={keyword}"
        self.set_page(search_page)
        time.sleep(3)
        self.refresh_selenium()

        links_num = 0
        tries_count = 0

        while True:
            self.go_bottom()
            new_links_num = len(self.page.query_selector_all(self.selectors["group_link"]))
            if new_links_num == links_num:
                tries_count += 1
            else:
                links_num = new_links_num
                self.refresh_selenium()

            if tries_count == 3:
                break

        links = [element.get_attribute("href") for element in self.page.query_selector_all(self.selectors["group_link"])]
        print(f"{len(links)} groups found and saved")

        if links:
            self.json_data["groups"] = links
            with open(self.data_path, "w", encoding="UTF-8") as file:
                json.dump(self.json_data, file, indent=4)
