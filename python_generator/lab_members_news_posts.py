import glob
import os
import random
import re
from datetime import datetime

import pycountry
import yaml

from python_generator import constants

# List of templates for each month
welcome_templates = [
    [
        "We would like to welcome our new member, {name} from {country}. {first_name} will be working on {keywords}. We hope you have a great time in our lab!",
        "We are delighted to welcome our newest team member, {name} from {country}. {first_name} will be contributing to {keywords}. Have a fantastic time with us!",
        "Welcome to our lab, {name} from {country}. {first_name} will be focusing on {keywords}. We're excited to have you here!"
    ],
    [
        "We are excited to welcome {name} from {country} who joined us this month. {first_name} is focusing on {keywords}. Wishing you a successful time with us!",
        "Excited to have {name} from {country} joining our team this month. {first_name} will work on {keywords}. Best of luck!",
        "Join us in welcoming {name} from {country}. {first_name} will focus on {keywords}. Hope you have a fruitful time with us!"
    ],
    [
        "A warm welcome to {name} from {country}, joining us this month! {first_name} will be working on {keywords}. We look forward to your contributions!",
        "Let's warmly welcome {name} from {country} who will be working on {keywords}. Excited for your contributions!",
        "Welcome {name} from {country} to our team. {first_name} will be involved in {keywords}. Looking forward to your work!"
    ],
    [
        "Introducing {name} from {country}, who is now part of our team. {first_name} will be working on {keywords}. Welcome aboard and best of luck!",
        "Meet {name} from {country}, the newest member of our team. {first_name} will focus on {keywords}. Best wishes!",
        "We're pleased to introduce {name} from {country}. {first_name} will research {keywords}. Welcome to the team!"
    ],
    [
        "Join us in welcoming {name} from {country} to our team. {first_name} will study {keywords}. We are glad to have you with us!",
        "Let's all welcome {name} from {country} to our group. {first_name} will work on {keywords}. Happy to have you!",
        "Please welcome {name} from {country}. {first_name} will be focusing on {keywords}. Excited to have you on board!"
    ],
    [
        "Let's welcome our new member, {name} from {country}. {first_name} will be working on {keywords}. Excited to see what you achieve with us!",
        "A warm welcome to {name} from {country}. {first_name} will focus on {keywords}. Looking forward to your achievements!",
        "Join us in welcoming {name} from {country}. {first_name} will be working on {keywords}. Eager to see your success!"
    ],
    [
        "We happily welcome {name} from {country} to our lab. {first_name} is set to work on {keywords}. Here's to a productive journey together!",
        "A warm welcome to {name} from {country} to our team. {first_name} will be focusing on {keywords}. Looking forward to a productive time together!",
        "Join us in welcoming {name} from {country}. {first_name} will contribute to our understanding of {keywords}. Here's to a successful journey!"
    ],
    [
        "A big welcome to {name} from {country}, who has joined us this month. {first_name} will focus on {keywords}. Looking forward to your success!",
        "We're excited to have {name} from {country} join us. {first_name} will be working on {keywords}. Best of luck for your success!",
        "Welcome {name} from {country}, joining us this month. {first_name} will focus on {keywords}. Looking forward to your contributions!"
    ],
    [
        "Welcome {name} from {country} to our team! {first_name} will be dealing with {keywords}. Best wishes for your time here!",
        "A warm welcome to {name} from {country}. {first_name} will focus on {keywords}. Wishing you all the best!",
        "Introducing {name} from {country}. {first_name} will be working on {keywords}. Best of luck in your endeavors!"
    ],
    [
        "Introducing {name} from {country}, joining our lab this month. {first_name} will be working on {keywords}. We hope you thrive with us!",
        "Let's welcome {name} from {country}, who joined us this month. {first_name} will focus on {keywords}. Hoping for your success!",
        "Welcome {name} from {country} to our lab. {first_name} will be working on {keywords}. Thrilled to have you with us!"
    ],
    [
        "We are thrilled to have {name} from {country} join us. {first_name} will be focusing on {keywords}. Wishing you a great experience in our lab!",
        "Thrilled to welcome {name} from {country} to our team. {first_name} will work on {keywords}. Hope you have a great time!",
        "Excited to have {name} from {country} with us. {first_name} will focus on {keywords}. Wishing you a wonderful experience!"
    ],
    [
        "Please join us in welcoming {name} from {country}. {first_name} will be working on {keywords}. We are excited to have you on board!",
        "Join us in welcoming {name} from {country}. {first_name} will focus on {keywords}. Excited to have you with us!",
        "Let's welcome {name} from {country}. {first_name} will be working on {keywords}. Thrilled to have you on our team!"
    ]
]


def add_and_after_last_delimiter(input_str: str):
    # Find the position of the last comma or semicolon
    # Find the position of the last comma or semicolon
    pos_comma = input_str.rfind(',')
    pos_semicolon = input_str.rfind(';')

    # Determine which delimiter appears last
    if pos_comma > pos_semicolon:
        pos = pos_comma
        delimiter = ','
    else:
        pos = pos_semicolon
        delimiter = ';'

    # If no delimiter is found, return the original string
    if pos == -1:
        return input_str

    keywords_list = [f.strip().replace(delimiter, "") for f in input_str.split(f'{delimiter}') if
                     f.strip().replace(delimiter, "").strip()]

    result = ', '.join(keywords_list[:-1]) + ', and ' + keywords_list[-1]

    return result.replace(";", ",")


def get_random_element_with_seed(input_number, your_list):
    random.seed(input_number)
    return random.choice(your_list)


def is_valid_date(date_str):
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def generate_welcome_post_internal(name, date_in, photo, country, keywords, posts_dir):
    # Determine the month to select the template
    month = datetime.strptime(date_in, '%Y-%m-%d').month - 1  # Adjust for 0-based index
    day = datetime.strptime(date_in, '%Y-%m-%d').day
    template = get_random_element_with_seed(day, welcome_templates[month])
    photo_template = f"![]({photo})" if photo else ""
    thumbnail_template = f"thumbnail: \"'{photo}'\"" if photo else ""
    first_name = name
    try:
        first_name = re.match(r'^\w+', name).group()
    except:
        print("Lab members: Can't determine first name from", name)

    post_content = f"""---
layout: double
title: "Welcome, {name}!"
date: "{date_in}"
{thumbnail_template}
---
        {template.format(name=name, country=country, keywords=keywords, first_name=first_name)}
        {photo_template}

        """.replace("from UNKNOWN COUNTRY", "").replace(" . ", ". ")

    post_content = re.sub(r' +', ' ', post_content)
    post_filename = os.path.join(posts_dir, f"{date_in}-Welcome-new-member-{name.replace(' ', '-')}.md")

    with open(post_filename, 'w', encoding="utf-8") as post_file:
        post_file.write(post_content)


def read_md_files_as_dicts(directory):
    file_pattern = os.path.join(directory, '*.md')
    md_files = glob.glob(file_pattern)

    md_dicts = []

    for file_path in md_files:
        with open(file_path, 'r', encoding='utf-8') as file:
            # Read the YAML front matter
            content = file.read()
            if content.startswith('---'):
                end_idx = content.find('---', 3)
                if end_idx != -1:
                    yaml_content = content[3:end_idx].strip()
                    try:
                        yaml_data = yaml.safe_load(yaml_content)
                        md_dicts.append(yaml_data)
                    except yaml.YAMLError as e:
                        print(f"Lab members: Error parsing YAML in {file_path}: {e}")

    return md_dicts


def generate_welcome_posts(entry, site_dir):
    posts_dir = os.path.join(site_dir, constants.POSTS_DIR)

    name = entry.get('name', None)
    if not name:
        return
    date_in = entry.get('date_joined')
    date_in_present = True if date_in and is_valid_date(date_in) else False
    if not date_in_present:
        return
    photo = entry.get('photo')
    country = entry.get('country') if entry.get('country') else 'UNKNOWN COUNTRY'
    if country != "UNKNOWN COUNTRY":
        country_input = country.replace("the ", "")
        country = country + (
            (" " + pycountry.countries.get(name=country_input).flag) if pycountry.countries.get(
                name=country_input) else "")
    else:
        country = "somewhere around the globe"
    keywords = add_and_after_last_delimiter(entry.get('keywords')) if entry.get(
        'keywords') else 'various projects related to cellular senescence and ageing'
    generate_welcome_post_internal(name=name,
                                   date_in=date_in,
                                   keywords=keywords,
                                   photo=photo,
                                   country=country,
                                   posts_dir=posts_dir
                                   )
