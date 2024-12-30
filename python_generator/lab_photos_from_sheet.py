import os.path
import shutil
import traceback

import requests

from python_generator import constants
from python_generator.utils import safe_file_name
from python_generator.utils import remove_thumbnail_segment_from_url, read_published_google_sheet, download_pic, \
    get_dir_path


def attempt_to_download_photo(photo_dict, site_dir, key="photo"):
    gallery_dir = get_dir_path(site_dir, constants.GALLERY_DIR)

    photo = photo_dict.get(key)
    title = photo_dict.get("title")
    location = photo_dict.get("location")
    date = photo_dict.get("date")

    if photo and title and date:
        os.makedirs(gallery_dir, exist_ok=True)
        location_segment = f"-{location}" if location else ""
        image_filename = f"{date}-{safe_file_name(title)}{safe_file_name(location_segment)}.webp"
        target_path = os.path.join(gallery_dir, image_filename)
        target_path_abs = os.path.join(site_dir, target_path)

        try:
            photo = remove_thumbnail_segment_from_url(photo)
            response = requests.get(photo)
            response.raise_for_status()
            # Convert image to webp format
            with open(target_path_abs, 'wb') as img_file:
                img_file.write(response.content)
                return image_filename

        except requests.exceptions.RequestException:
            print("Lab photos: Error occurred while downloading photo")
            return None

    else:
        return None


def write_photo_news_post(meta_data: dict, primary_photos, additional_photos, site_dir):
    title = meta_data.get("title")
    date = meta_data.get("date")
    description = meta_data.get("description")
    location = meta_data.get("location")
    if not title or not date:
        return
    local_urls = []
    for i, img in enumerate(additional_photos):
        img_suffix = i + 1

        img_folder = os.path.join(site_dir, 'assets', "posts")
        os.makedirs(img_folder, exist_ok=True)
        output_name = download_pic(img_url=img,
                                   formatted_title=safe_file_name(title),
                                   img_suffix=img_suffix,
                                   img_folder=img_folder)

        if output_name:
            local_urls.append(f"/assets/posts/{output_name}")

    if primary_photos and local_urls:
        primary_photos = F"/gallery/{primary_photos}"
        additional_photo_contents = "\n".join(["![](" + d + ")" for d in local_urls])

        post_content = f"""---
layout: double
title: \"{title}\"
date: {date}
album: \"{title}\"
thumbnail: \"{primary_photos}\"
---

 {f"📌 {location}" if not description else f"{description}"}
 
![]({primary_photos})
{additional_photo_contents}

"""
        posts_dir = get_dir_path(site_dir, constants.POSTS_DIR)

        post_filename = os.path.join(posts_dir, f"{date}-{title}.md")
        with open(post_filename, 'w', encoding="utf-8") as post_file:
            post_file.write(post_content)


def process(args):
    try:
        print("Processing photos")

        site_dir = args[constants.ARG_SITE_DIR]
        data = read_published_google_sheet(args[constants.ARG_PHOTOS_SHEET_ID])["data"]
        data = [d for d in data if d.get("title") and d.get("photo") and d.get("date")]

        gallery_dir = get_dir_path(site_dir, constants.GALLERY_DIR)
        shutil.rmtree(gallery_dir)

        for entry in data:
            output_path_primary_photo = attempt_to_download_photo(entry, site_dir=site_dir)
            if output_path_primary_photo:
                filtered_dict: dict = {k: v for k, v in entry.items() if "additional" in k and v}
                if len(filtered_dict) > 0:
                    write_photo_news_post(entry, output_path_primary_photo, filtered_dict.values(),
                                          site_dir=site_dir)

    except:
        print("An error occurred in photos processor")
        traceback.print_exc()
