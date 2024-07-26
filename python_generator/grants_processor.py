import os
import traceback
from datetime import datetime

import yaml
from python_generator import constants
from python_generator import utils


def process(args):
    try:
        print("Processing grants")

        site_dir = args[constants.ARG_SITE_DIR]
        data = utils.read_published_google_sheet(args[constants.ARG_GRANTS_SHEET_ID])["data"]
        current_year = datetime.now().year
        data = [d for d in data if d.get("title") and int(d.get("until", 0)) >= current_year]

        img_output_folder = utils.get_dir_path(os.path.join(site_dir, 'assets', "icon"))
        os.makedirs(img_output_folder, exist_ok=True)
        for item in data:
            photo_data = item.get("photo")
            if "https://" in photo_data:
                new_url = utils.download_pic(img_url=photo_data,
                                             formatted_title=utils.safe_file_name(item.get("title")),
                                             img_suffix="grants",
                                             img_folder=img_output_folder)
                item["photo"] = '/assets/icon/' + new_url

        with open(os.path.join(utils.get_dir_path(site_dir, constants.DATA_DIR), "grants.yml"), 'w',
                  encoding="utf-8") as file:
            yaml.dump(data, file)

    except:
        print("An error occurred in photos processor")
        traceback.print_exc()
