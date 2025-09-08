import os

from python_generator import constants
from python_generator import utils


def save_research_doc_as_markdown(site_dir, doc_id):
    doc_contents = utils.google_doc_to_markdown(doc_id, utils.get_dir_path(site_dir, constants.POSTS_DIR))
    markdown_content = doc_contents["markdown_content"]
    wrapped_md = f"""---
layout: default
title: Research
header-title: Our research
permalink: /research/
---
<div class="container-xl">
<div class="blog py-3 py-md-5">
{{% capture markdown %}}
{markdown_content}
{{% endcapture %}}
{{{{ markdown | markdownify }}}}
</div>
</div>
"""

    with open(os.path.join(site_dir, "research.markdown"), 'w', encoding='utf-8') as md_file:
        md_file.write(wrapped_md)


def process(args):
    pass
    # try:
    #     print("Processing research document")
    #     site_dir = args[constants.ARG_SITE_DIR]
    #     doc_id = args[constants.ARG_RESEARCH_DOC_ID]
    #     save_research_doc_as_markdown(site_dir=site_dir, doc_id=doc_id)
    # except Exception:
    #     print("An error occurred in research document processor")
    #     traceback.print_exc()
