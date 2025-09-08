import os
import traceback

from python_generator import constants
from python_generator import utils


def save_custom_news_doc_as_markdown(doc_id, posts_dir):
    doc_contents = utils.google_doc_to_markdown(doc_id, posts_dir)
    original_dir = os.getcwd()
    os.chdir(posts_dir)
    has_fixed_headers = doc_contents["has_fixed_headers"]
    title_part = doc_contents["title_part"]
    date_part = doc_contents["date_part"]
    first_image_url = doc_contents["first_image_url"]
    markdown_content = doc_contents["markdown_content"]
    formatted_title = doc_contents["formatted_title"]
    # Add Jekyll header
    layout_type = has_fixed_headers and 'double' or 'single'

    header = f"---\nlayout: {layout_type}\ntitle: \"{title_part}\"\ndate: {date_part}\nthumbnail: \"{first_image_url}\"\n---\n\n"

    # Save the Markdown to the specified file with the formatted title as the name
    with open(f"{formatted_title.replace('_', '-')}.md", 'w', encoding='utf-8') as md_file:
        md_file.write(header + markdown_content)

    os.chdir(original_dir)


def process(args):
    print("Processing custom news articles")
    site_dir = args[constants.ARG_SITE_DIR]
    posts_dir = utils.get_dir_path(site_dir, constants.POSTS_DIR)
    custom_news_articles = utils.extract_urls_from_gdoc(args[constants.ARG_CUSTOM_NEWS_ARTICLES_ID],
                                                        output_dir=posts_dir)
    custom_news_articles = [f for f in custom_news_articles if f]

    for article in custom_news_articles:
        save_custom_news_doc_as_markdown(article, posts_dir=posts_dir)
