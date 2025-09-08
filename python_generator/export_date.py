def export_build_date(path):
    # !/usr/bin/env python3
    from pathlib import Path
    from datetime import datetime

    # Get current system date
    date_str = datetime.now().strftime("%d-%B-%Y")

    # Path to the Jekyll site's _data directory (relative to this script file)
    out_file = Path(path, "last_update.yml")

    # Ensure directory exists and write YAML
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(f"date: '{date_str}'\n", encoding="utf-8")

    print(f"Wrote last update to: {out_file}")
