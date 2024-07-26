import argparse
import os

from python_generator import constants
from python_generator.utils import reduce_images_in_dir


def main(args_dict: dict):
    from python_generator.custom_news_articles_processor import process as process_custom_news
    from python_generator.lab_members_script_sheets import process as process_members
    from python_generator.lab_photos_from_sheet import process as process_photos
    from python_generator.publications import process as process_publications
    from python_generator.research_page import process as process_research_page
    from python_generator.grants_processor import process as process_grants

    args_dict[constants.ARG_SITE_DIR] = os.path.abspath(args_dict[constants.ARG_SITE_DIR])
    print("Outputting to", args_dict[constants.ARG_SITE_DIR])

    process_publications(args_dict)
    process_members(args_dict)
    process_custom_news(args_dict)
    process_photos(args_dict)
    process_research_page(args_dict)
    process_grants(args_dict)

    site_dir = args_dict[constants.ARG_SITE_DIR]

    reduce_images_in_dir(os.path.join(site_dir, constants.GALLERY_DIR))
    reduce_images_in_dir(os.path.join(site_dir, "assets", "posts"))
    reduce_images_in_dir(os.path.join(site_dir, "assets", "members"))


def run():
    parser = argparse.ArgumentParser(description="Process some inputs.")
    parser.add_argument("--site_dir", required=True, type=str,
                        help="Main dir of jekyll site, where the config file is located")
    parser.add_argument("--custom_news_articles_doc_id", required=True, type=str,
                        help="ID of the custom news articles document")
    parser.add_argument("--members_sheet_id", required=True, type=str,
                        help="ID of the lab members sheet")
    parser.add_argument("--photos_sheet_id", required=True, type=str,
                        help="ID of the lab photos sheet")
    parser.add_argument("--selected_publications_sheet_id", required=True, type=str,
                        help="ID of the selected papers sheet")
    parser.add_argument("--research_doc_id", required=True, type=str,
                        help="ID of the research document")
    parser.add_argument("--grants_sheet_id", required=True, type=str,
                        help="ID of the grants sheet")
    args = parser.parse_args()

    main(vars(args))
