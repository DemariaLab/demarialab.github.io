import hashlib
import random
import re
import shutil
import string
from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse, unquote

import html2text
import requests
import unicodedata
from bs4 import BeautifulSoup


# Function to create a safe file name
def safe_file_name(input_string, replacement_char='_'):
    # Remove or replace characters that are not safe for file names
    safe_string = re.sub(r'[\/:*?"<>|]', replacement_char, input_string)

    # Remove leading and trailing spaces and dots
    safe_string = safe_string.strip(' .')

    # Ensure the file name is not empty
    if not safe_string:
        safe_string = 'unnamed'

    # Limit the file name length to a reasonable size (e.g., 255 characters)
    max_length = 255
    if len(safe_string) > max_length:
        safe_string = safe_string[:max_length]

    return safe_string


from PIL import ImageEnhance

from PIL import Image, ImageFilter
import os


def blur_images_in_dir(input_dir, blur_radius=30, reduced_size=(56, 56)):
    if not os.path.isdir(input_dir):
        return

    # Valid image extensions
    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')

    # Loop through all files in the directory
    for filename in os.listdir(input_dir):
        # Check if the file has a valid image extension
        if not filename.startswith("blurred_") and not filename.startswith("reduced_") and filename.lower().endswith(
                valid_extensions):
            filepath = os.path.join(input_dir, filename)
            # Open an image file
            with Image.open(filepath) as img:
                # Apply blur
                blurred_img = img.filter(ImageFilter.GaussianBlur(blur_radius))
                # Reduce the size of the image
                reduced_blurred_img = blurred_img.resize(reduced_size)
                # Prepare the output file path
                blurred_filename = f'blurred_{os.path.splitext(filename)[0]}.webp'
                blurred_filepath = os.path.join(input_dir, blurred_filename)
                # Save the blurred and reduced image in WebP format with medium quality
                reduced_blurred_img.save(blurred_filepath, format='WEBP', quality=50)


def reduce_images_in_dir(input_dir, sharpness_factor=0.8):
    if not os.path.isdir(input_dir):
        return

    # Valid image extensions
    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')

    # Loop through all files in the directory
    for filename in os.listdir(input_dir):
        # Check if the file has a valid image extension
        if not filename.startswith("reduced_") and filename.lower().endswith(valid_extensions):
            filepath = os.path.join(input_dir, filename)
            # Open an image file
            with Image.open(filepath) as img:
                # Get original dimensions
                original_width, original_height = img.size
                # Calculate reduced dimensions
                reduced_width, reduced_height = original_width * 2 // 3, original_height * 2 // 3
                # Reduce the size of the image
                reduced_img = img.resize((reduced_width, reduced_height))
                # Apply sharpening enhancement
                enhancer = ImageEnhance.Sharpness(reduced_img)
                sharpened_img = enhancer.enhance(sharpness_factor)
                # Prepare the output file path
                reduced_filename = f'reduced_{os.path.splitext(filename)[0]}.webp'
                reduced_filepath = os.path.join(input_dir, reduced_filename)
                # Save the reduced and sharpened image in WebP format with medium quality
                sharpened_img.save(reduced_filepath, format='WEBP', quality=min(100, int(sharpness_factor * 100)))


def read_published_google_sheet(sheet_id):
    url = f"https://docs.google.com/spreadsheets/d/e/{sheet_id}/pubhtml"
    # Fetch the HTML content
    response = requests.get(url)
    response.raise_for_status()

    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract table rows
    table = soup.find('table')
    rows = table.find('tbody').find_all('tr')
    # Extract column headers
    headers = [header.get_text().strip().lower().replace(' ', '_') for header in rows[0].find_all('td')]
    # Extract data rows
    data = []
    for row in rows[1:]:
        cells = row.find_all('td')
        record = {}
        for i, cell in enumerate(cells):
            column_name: str = replace_special_chars(headers[i], sep="_").strip().replace("_yyyy_mm_dd_", "").replace(
                "_separated_by_", "").lower()
            if "photo" in column_name and "additional" not in column_name:
                column_name = "photo"
            if column_name.lower().startswith("keyword"):
                column_name = "keywords"
            if column_name:
                record[column_name] = extract_cell_data(cell)
        data.append(record)

    return {'headers': headers, 'data': data}


def get_dir_path(*path_segments):
    path = os.path.join(*path_segments)
    os.makedirs(path, exist_ok=True)
    return path


def remove_thumbnail_segment_from_url(url: str):
    return re.sub(r"=w\d+-h\d+", "", url) if url else None


# Function to extract image URLs from the HTML content of a cell
def extract_cell_data(cell):
    img_tag = cell.find('img')
    return img_tag['src'] if img_tag else cell.get_text().strip()


def extract_urls_from_gdoc(doc_id, output_dir, checksum_file_name='checksum_custom_posts'):
    input_url = f"https://docs.google.com/document/d/{doc_id}/export?format=html"
    response = requests.get(input_url)

    if response.status_code == 200:
        html_content = response.text

        urls = re.findall(r'(https?://[^\s"<>]+)', html_content)
        urls = [get_final_url_and_extract_doc_id(f) for f in urls]
        if len(urls) > 0:
            current_checksum = compute_checksum("\n".join(urls))
            checksum_file = os.path.join(output_dir, checksum_file_name)
            # Check if checksum file exists and read it
            if os.path.exists(checksum_file):
                with open(checksum_file, 'r', encoding='utf-8') as f:
                    previous_checksum = f.read().strip()
            else:
                previous_checksum = None

            if previous_checksum == current_checksum:
                print("Document has not changed. Exiting.")
                return []

                # Save the current checksum to the file
            with open(checksum_file, 'w', encoding='utf-8') as f:
                f.write(current_checksum)
            return urls if len(urls) > 0 else []
        else:
            return []
    else:
        return []


# Function to sanitize the title for filenames
def sanitize_title(title):
    return re.sub(r'[^\w\s-]', '', title)


def extract_filename_from_content_disposition(content_disposition):
    # Extract filename from Content-Disposition header
    if content_disposition:
        # Try to find filename*
        filename_match = re.search(r'filename\*=[^\'\s]*\'\'(?P<filename>.+)', content_disposition)
        if filename_match:
            filename = unquote(filename_match.group('filename')).strip()
            return filename
        # Fallback to filename if filename* is not found
        filename_match = re.search(r'filename=\"(?P<filename>[^\"]+)\"', content_disposition)
        if filename_match:
            filename = filename_match.group('filename').strip()
            return filename
    return "Untitled.html"


def extract_title_part(document_title):
    # Extract title part by removing the date segment if present
    title_part_match = re.search(r'(\d{4}-\d{2}-\d{2})-(.*)', document_title)
    if title_part_match:
        return [title_part_match.group(1).strip(), title_part_match.group(2).strip()]
    return [None, document_title]


def has_fixed_page_headers(html_content):
    # Check if the HTML content contains fixed headers (div tags inside the body tag)
    soup = BeautifulSoup(html_content, 'html.parser')
    body_tag = soup.body
    if body_tag:
        # Find all div elements directly inside the body
        div_elements = body_tag.find_all('div', recursive=False)
        for div in div_elements:
            # Check if the div contains content that indicates a header
            if div.text.strip():  # You may adjust this condition based on specific content of your headers
                return True
    return False


def download_pic(img_url, formatted_title, img_suffix, img_folder):
    img_data = requests.get(remove_thumbnail_segment_from_url(img_url)).content
    if not img_data:
        return None
    try:
        img_folder = get_dir_path(img_folder)
        img_obj = Image.open(BytesIO(img_data))

        # Determine the best format based on the image format
        if img_obj.format == 'PNG':
            img_filename = f"{formatted_title}-{img_suffix}.png"
        else:
            img_filename = f"{formatted_title}-{img_suffix}.webp"

        img_path = os.path.join(img_folder, img_filename)
        img_obj.save(img_path)
    except:
        # If download or save fails, check if the original image is PNG
        try:
            img_obj = Image.open(BytesIO(img_data))
            if img_obj.format == 'PNG':
                img_filename = ''.join(random.choices(string.ascii_letters + string.digits, k=8)) + '.png'
            else:
                img_filename = ''.join(random.choices(string.ascii_letters + string.digits, k=8)) + '.webp'
        except:
            img_filename = ''.join(random.choices(string.ascii_letters + string.digits, k=8)) + '.webp'

        img_path = os.path.join(img_folder, img_filename)
        with open(img_path, 'wb') as img_file:
            img_file.write(img_data)
    return img_filename


def download_images_and_update_links(html_content, formatted_title, output_dir):
    soup = BeautifulSoup(html_content, 'html.parser')
    img_tags = soup.find_all('img')
    parent_dir = os.path.dirname(output_dir)
    img_folder = os.path.join(parent_dir, 'assets', "posts")
    os.makedirs(img_folder, exist_ok=True)

    for i, img in enumerate(img_tags):
        img_url = img['src']
        img_suffix = i + 1

        output_name = download_pic(img_url=img_url,
                                   formatted_title=formatted_title,
                                   img_suffix=img_suffix,
                                   img_folder=img_folder)

        if output_name:
            img['src'] = f"/assets/posts/{output_name}"

    return str(soup), img_tags[0]['src'] if img_tags else None


def compute_checksum(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def get_final_url_and_extract_doc_id(initial_url):
    """
    Used as part of extract_urls_from_gdoc method
    """
    regex_pattern = r'/d/([\w|\d]+?)/'
    match = re.search(regex_pattern, initial_url)

    if match:
        return match.group(1)
    # Follow the URL redirections to get the final URL
    response = requests.get(initial_url)
    final_url = response.url

    # Parse the URL and extract the doc ID
    parsed_url = urlparse(final_url)
    path_segments = parsed_url.path.split('/')
    if 'document' in path_segments:
        doc_id_index = path_segments.index('d') + 1
        doc_id = path_segments[doc_id_index]
        return doc_id
    return None


def google_doc_to_markdown(doc_id, output_dir):
    # Save the current working directory and change to output directory
    original_dir = os.getcwd()
    os.chdir(output_dir)
    html_filepath = None
    try:
        # Fetch the document content as HTML
        input_url = f"https://docs.google.com/document/d/{doc_id}/export?format=html"
        response = requests.get(input_url)
        response.raise_for_status()
        html_content = response.text

        # Save the HTML file in the output directory
        content_disposition = response.headers.get('Content-Disposition')
        html_filename = extract_filename_from_content_disposition(content_disposition)
        html_filepath = os.path.join(os.getcwd(), html_filename)

        with open(html_filepath, 'w', encoding='utf-8') as html_file:
            html_file.write(html_content)

        # Extract title from the saved HTML file name (without extension)
        document_title = re.sub(r'\.html$', '', html_filename)

        # Format title for output file
        formatted_title = replace_special_chars(re.sub(r'[^\w\s-]', '', document_title).strip())
        formatted_title = formatted_title[0:min(30, len(formatted_title))]

        # Extract title part for the Jekyll header
        date_part, title_part = extract_title_part(document_title)

        # Check if the document has fixed headers
        has_fixed_headers = has_fixed_page_headers(html_content)

        # Download images and update HTML content
        html_content, first_image_url = download_images_and_update_links(html_content, formatted_title, output_dir)

        # Convert HTML to Markdown
        h = html2text.HTML2Text()
        h.ignore_links = False
        markdown_content = h.handle(html_content)

        return {"has_fixed_headers": has_fixed_headers,
                "title_part": title_part,
                "date_part": date_part,
                "html_content": html_content,
                "first_image_url": first_image_url,
                "markdown_content": markdown_content,
                "formatted_title": formatted_title
                }
    finally:
        # Revert back to the original working directory
        os.chdir(original_dir)
        # Delete the HTML file
        if html_filepath and os.path.exists(html_filepath):
            os.remove(html_filepath)


def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])


def generate_last_name_initials(full_name):
    # Split the full name into parts by whitespace
    parts = full_name.split()

    # First part is considered for initials, last part for last name
    if len(parts) > 1:
        first_word = parts[0]
        last_name = parts[-1]

        # Check for dashes in the first word
        if '-' in first_word:
            # Split first word by dash
            initial_parts = first_word.split('-')
            initials = initial_parts[0][0].upper() + initial_parts[1][0].upper()
        else:
            initials = first_word[0].upper()
    else:
        last_name = parts[0]
        initials = ''

    # Construct the result
    result = last_name + ' ' + initials

    return result


def is_date_older_than_now(date_str):
    # Check if the input is None or empty
    if not date_str:
        return "false"
    try:
        # Try to parse the input date string
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        # If parsing fails, return "false"
        return "false"
    # Get today's date
    today = datetime.today()
    # Compare the dates
    return "true" if date_obj < today else "false"


def delete_dir_contents(dir_path):
    if not os.path.isdir(dir_path):
        return
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        if os.path.isfile(item_path) or os.path.islink(item_path):
            os.unlink(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)


def replace_special_chars(text, sep="_"):
    # Replace one or more special characters with a single underscore
    return re.sub(r'[^a-zA-Z0-9]+', sep, text)
