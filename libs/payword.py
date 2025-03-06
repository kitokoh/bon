import os
import time
import json
import random
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright, Browser, Page

class WebScraping:
    def __init__(self, headless: bool = False, time_out: int = 0,
                 proxy_server: str = "", proxy_port: str = "", proxy_user: str = "", proxy_pass: str = "",
                 user_data_dir: str = "", user_agent: bool = False,
                 download_path: str = "", extensions: List[str] = [], incognito: bool = False,
                 start_killing: bool = False, start_openning: bool = True, width: int = 1280, height: int = 720,
                 mute: bool = True):
        self.basetime = 1
        self.current_folder = os.path.dirname(__file__)
        self.__headless__ = headless
        self.__proxy_server__ = proxy_server
        self.__proxy_port__ = proxy_port
        self.__proxy_user__ = proxy_user
        self.__proxy_pass__ = proxy_pass
        self.__user_data_dir__ = user_data_dir
        self.__user_agent__ = user_agent
        self.__download_path__ = download_path
        self.__extensions__ = extensions
        self.__incognito__ = incognito
        self.__start_openning__ = start_openning
        self.__width__ = width
        self.__height__ = height
        self.__mute__ = mute
        self.__web_page__: Optional[str] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

        if start_killing:
            self.kill_browsers()

        if self.__start_openning__:
            self.__set_browser_instance__()

        if time_out > 0:
            self.page.set_default_timeout(time_out * 1000)

    def kill_browsers(self):
        # Implement browser killing logic if necessary
        pass

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

        if self.__user_data_dir__:
            browser_options["args"].append(f"--user-data-dir={self.__user_data_dir__}")

        if self.__proxy_server__ and self.__proxy_port__:
            browser_options["proxy"] = {
                "server": f"{self.__proxy_server__}:{self.__proxy_port__}"
            }
            if self.__proxy_user__ and self.__proxy_pass__:
                browser_options["proxy"]["username"] = self.__proxy_user__
                browser_options["proxy"]["password"] = self.__proxy_pass__

        self.browser = browser_type.launch(**browser_options)
        self.page = self.browser.new_page()

    def set_cookies(self, cookies: List[Dict[str, Any]]):
        self.page.context.add_cookies(cookies)

    def screenshot(self, base_name: str):
        if not base_name.endswith(".png"):
            base_name += ".png"
        self.page.screenshot(path=base_name)

    def full_screenshot(self, path: str):
        self.page.screenshot(path=path, full_page=True)

    def get_browser(self) -> Browser:
        return self.browser

    def end_browser(self):
        self.browser.close()
        self.page = None
        self.browser = None

    def send_data(self, selector: str, data: str):
        self.page.fill(selector, data)

    def click(self, selector: str):
        self.page.click(selector)

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

    def click_js(self, selector: str):
        self.page.evaluate(f"document.querySelector('{selector}').click()")

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

        super().__init__(user_data_dir=os.getenv("CHROME_FOLDER"), start_killing=True, user_agent=True)

    def post_in_groupsx(self):
        posts_done = []
        group = random.choice(self.json_datax["groups"])
        self.set_page(group)
        time.sleep(5)
        self.refresh_selenium()

        post_text = random.choice(self.json_datax["posts"])
        post_images = random.sample(self.json_datax["images"], min(30, len(self.json_datax["images"])))

        try:
            self.click_js(self.selectors["display_input"])
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
