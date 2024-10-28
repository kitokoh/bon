import os
import json
import random
from dotenv import load_dotenv
from libs.logs import logger
from time import sleep
from libs.automate import WebScraping

# Read env vars
load_dotenv()
CHROME_FOLDER = os.getenv("CHROME_FOLDER")
WAIT_MIN = int(os.getenv("WAIT_MIN"))


class Scraper(WebScraping):

    def __init__(self):
        """Read data from JSON files and start scraper using chrome folder."""
        current_folder = os.path.dirname(__file__)
        parent_folder = os.path.dirname(current_folder)
        self.data_path = os.path.join(parent_folder, "data.json")
        self.data_pathx = os.path.join(parent_folder, "data1.json")

        self.selectors_path = os.path.join(parent_folder, "config", "selectors.json")

        # Read JSON data
        with open(self.data_path, encoding="UTF-8") as file:
            self.json_data = json.load(file)
        with open(self.data_pathx, encoding="UTF-8") as file:
            self.json_datax = json.load(file)

        # Load selectors from JSON file
        with open(self.selectors_path, encoding="UTF-8") as file:
            self.selectors = json.load(file)

        # Start scraper
        super().__init__(chrome_folder=CHROME_FOLDER, start_killing=True)


    def post_in_groupsx(self):
        """Publish each post in each group from data file."""
        posts_done = []
        
        # Choisit aléatoirement un groupe
        group = random.choice(self.json_datax["groups"])
        self.set_page(group)
        sleep(5)
        self.refresh_selenium()

        # Choisit aléatoirement un post
        post_text = random.choice(self.json_datax["posts"])

        # Choisit aléatoirement jusqu'à 30 images
        post_images = random.sample(self.json_datax["images"], min(30, len(self.json_datax["images"])))

        # Ouvre la zone de texte pour le post
        try:
            self.click_js(self.selectors["display_input"])
        except Exception:
            logger.error(f'Erreur en ouvrant la zone de texte : "{post_text}" ({group})')
            return

        self.refresh_selenium()

        # Écrit le texte du post
        try:
            self.send_data(self.selectors["input"], post_text)
        except Exception:
            logger.error(f'Erreur en écrivant le texte : "{post_text}" ({group})')
            return

        # Télécharge les images sélectionnées
        for image_path in post_images:
            absolute_image_path = self.get_absolute_path(image_path)
            self.click_js(self.selectors["show_image_input"])
            self.refresh_selenium()
            self.send_data(self.selectors["add_image"], absolute_image_path)

        # Soumet le post
        self.refresh_selenium()
        try:
            self.click_js(self.selectors["submit"])
        except Exception:
            logger.error(f'Erreur en soumettant le post : "{post_text}" ({group})')
            return
        
        # Logs
        logger.info(f'Post réussi : "{post_text}" ({group})')
        posts_done.append([group, post_text])

        # Attends avant de poster dans un autre groupe
        sleep(WAIT_MIN * 60)
        



    def get_absolute_path(self, relative_path):
        """Convert a relative path to an absolute path based on project folder."""
        current_folder = os.path.dirname(__file__)
        return os.path.join(current_folder, relative_path)

    def post_in_groups(self):
        """Publish each post in each group from data file."""
        posts_done = []
        for group in self.json_data["groups"]:
            self.set_page(group)
            sleep(5)
            self.refresh_selenium()

            # Get random post
            post = random.choice(self.json_data["posts"])
            post_text = post["text"]
            post_image = post.get("image", "")

            # Open text input
            try:
                self.click_js(self.selectors["display_input"])
            except Exception:
                logger.error(f'Error opening text input: "{post}" ({group})')
                continue

            self.refresh_selenium()

            # Write text
            try:
                self.send_data(self.selectors["input"], post_text)
            except Exception:
                logger.error(f'Error writing text: "{post}" ({group})')
                continue

            # Upload image
            if post_image:
                absolute_image_path = self.get_absolute_path(post_image)
                self.click_js(self.selectors["show_image_input"])
                self.refresh_selenium()
                self.send_data(self.selectors["add_image"], absolute_image_path)

            # Submit
            self.refresh_selenium()
            try:
                self.click_js(self.selectors["submit"])
            except Exception:
                logger.error(f'Error submitting post: "{post_text}" ({group})')
                continue
            sleep(WAIT_MIN * 60)

            # Save register of post
            posts_done.append([group, post])

            # Logs
            logger.info(f'Post done: "{post_text}" ({group})')

    def save_groups(self, keyword):
        """Search already signed groups and save them in data file."""
        logger.info("Searching groups...")
        search_page = f"https://www.facebook.com/groups/search/groups/?q={keyword}"
        self.set_page(search_page)
        sleep(3)
        self.refresh_selenium()

        links_num = 0
        tries_count = 0

        # Scroll for showing already logged groups
        while True:
            self.go_bottom()
            new_links_num = len(self.get_elems(self.selectors["group_link"]))
            if new_links_num == links_num:
                tries_count += 1
            else:
                links_num = new_links_num
                self.refresh_selenium()

            if tries_count == 3:
                break

        # Get all links of the groups
        links = self.get_attribs(self.selectors["group_link"], "href")
        logger.info(f"{len(links)} groups found and saved")

        # Save links in JSON file
        if links:
            self.json_data["groups"] = links
            with open(self.data_path, "w", encoding="UTF-8") as file:
                json.dump(self.json_data, file, indent=4)














