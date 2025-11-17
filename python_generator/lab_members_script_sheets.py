import glob
import os.path
import re

import pycountry
import requests
import yaml

from python_generator import constants
from python_generator.lab_members_news_posts import generate_welcome_posts
from python_generator.utils import delete_dir_contents, remove_accents, \
    is_date_older_than_now, generate_last_name_initials, remove_thumbnail_segment_from_url
from python_generator.utils import read_published_google_sheet, get_dir_path


def extract_year(item):
    year = item["year"]
    if isinstance(year, int):
        return year
    year_str = str(year).split()[0].split('-')[0]
    return int(year_str)


def generate_profile_post(data: dict, site_dir):
    members_dir = get_dir_path(site_dir, constants.MEMBERS_DIR)

    name = data.get("name", None)
    qualification = data.get("qualification", None)
    role = data.get("role", None)
    photo = data.get("photo", None)
    date_joined = data.get("date_joined", None)
    date_leaving = data.get("date_leaving", None)
    country = data.get("country", None)
    previous_roles = data.get("previous_roles", None)
    keywords = data.get("keywords", None)
    biography = data.get("biography", None)
    is_alumni = is_date_older_than_now(date_leaving)
    research_name = generate_last_name_initials(remove_accents(name))
    if country:
        country_input = country.replace("the ", "")
        country = country + (
            (" " + pycountry.countries.get(name=country_input).flag) if
            pycountry.countries.get(name=country_input) else ""
        )

    photo_template = f"![]({photo})" if photo else ""
    keywords_present = keywords != "various projects related to cellular senescence and ageing"

    publications_path = os.path.join(get_dir_path(site_dir, constants.DATA_DIR), constants.FILE_ALL_PUBLICATIONS)
    if os.path.exists(publications_path) and os.path.isfile(publications_path):
        with open(publications_path, 'r', encoding="utf-8") as file:
            publications = yaml.safe_load(file)
            publications = sorted(publications, key=extract_year, reverse=True)
    else:
        publications = []
    last_name = name.split()[-1]
    first_name = name.split()[0]
    filtered_entries = [entry for entry in publications if
                        (f"{remove_accents(last_name)} {remove_accents(first_name)[0]}" in
                         remove_accents(entry.get('authors', ''))
                         or research_name.lower() in remove_accents(entry.get('authors', '')).lower())
                        ]
    publications = "; ".join(str(entry['pubmed_id']) for entry in filtered_entries)

    role_template = f'role: "{role}"' if role else ""
    date_in_template = f'date_joined: "{date_joined}"' if date_joined else ""
    date_out_template = f'date_leaving: "{date_leaving}"' if date_leaving else ""
    previous_roles_template = f'previous_roles: "{previous_roles}"' if previous_roles else ""
    keywords_template = f'keywords: "{keywords}"' if keywords_present else ""
    country_template = f'country: "{country}"' if country else ""
    qualification_template = f'qualification: "{qualification}"' if qualification else ""
    bio_template = f'biography: "{biography}"' if biography else ""
    publications_template = f'publications: "{publications}"' if publications else ""
    thumbnail_template = f"thumbnail: \"{photo}\"" if photo else ""
    is_alumni_template = f"is_alumni: {is_alumni}"
    research_name_template = f"last_name_initials: {research_name}"

    post_content = f"""---
layout: profile_template
name: "{name}"
unaccented_name: "{remove_accents(name)}"
{research_name_template}
{role_template}
{date_in_template}
{date_out_template}
{previous_roles_template}
{keywords_template}
{country_template}
{qualification_template}
{bio_template}
{publications_template}
{thumbnail_template}
{is_alumni_template}
---

    {photo_template}

            """.replace("from UNKNOWN COUNTRY", "").replace(" . ", ". ")

    post_content = re.sub(r' +', ' ', post_content)
    post_filename = os.path.join(members_dir, f"member_{name.replace(' ', '-')}.md")

    if not photo:
        return
    with open(post_filename, 'w', encoding="utf-8") as post_file:
        post_file.write(post_content)


def attempt_to_download_photo(member_dict, site_dir):
    photo = member_dict["photo"]
    name = member_dict["name"]
    if photo:
        photo = remove_thumbnail_segment_from_url(photo)

        # Attempt to download the image
        gallery_dir = os.path.join(r"assets", "members")
        os.makedirs(os.path.join(site_dir, gallery_dir), exist_ok=True)
        image_filename = f"member_{name.strip()}.webp"
        image_path = os.path.join(gallery_dir, image_filename)
        image_path_abs = os.path.join(site_dir, image_path)

        try:
            response = requests.get(photo)
            response.raise_for_status()
            # Convert image to webp format
            with open(image_path_abs, 'wb') as img_file:
                img_file.write(response.content)

            # Set member['photo'] to local path
            return ("/" if not image_path.startswith("/") else "") + image_path.replace('\\', '/')
        except requests.exceptions.RequestException:
            print("Lab members: Error occurred while downloading photo")
            return photo
    return photo


def process(args):
    print("Processing members")

    site_dir = args[constants.ARG_SITE_DIR]
    results = read_published_google_sheet(args[constants.ARG_MEMBERS_SHEET_ID])
    data = results["data"]
    data = [d for d in data if d.get("name")]

    for record in data:
        if record["photo"]:
            record["photo"] = attempt_to_download_photo(record, site_dir=site_dir)

    delete_dir_contents(get_dir_path(site_dir, constants.MEMBERS_DIR))
    posts_dir = get_dir_path(site_dir, constants.POSTS_DIR)

    # Check for existing files and delete them
    pattern = os.path.join(posts_dir, f"*-Welcome-new-member-*.md")
    existing_files = glob.glob(pattern)
    for file in existing_files:
        os.remove(file)

    for item in data:
        generate_profile_post(item, site_dir=site_dir)
        generate_welcome_posts(item, site_dir=site_dir)
