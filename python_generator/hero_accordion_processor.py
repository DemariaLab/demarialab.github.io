import os

import yaml

from python_generator import constants
from python_generator import utils


def process(args):
    print("Processing accordion items")

    site_dir = args[constants.ARG_SITE_DIR]
    data = utils.read_published_google_sheet(args[constants.ARG_HERO_ACCORDION_ITEMS])["data"]
    data = [d for d in data if d.get("title") and d.get("photo")]

    img_output_folder = utils.get_dir_path(os.path.join(site_dir, 'assets', "hero"))
    for item in data:
        photo_data = item.get("photo")
        if "https://" in photo_data:
            new_url = utils.download_pic(img_url=photo_data,
                                         formatted_title=utils.safe_file_name(item.get("title")),
                                         img_suffix="hero_photo",
                                         img_folder=img_output_folder)
            item["photo"] = '/assets/hero/' + new_url

    with open(os.path.join(utils.get_dir_path(site_dir, constants.DATA_DIR), "hero_accordion.yml"), 'w',
              encoding="utf-8") as file:
        yaml.dump(data, file)
