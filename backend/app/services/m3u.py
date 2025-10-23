import re
from typing import Dict, List


def parse_m3u(content: str) -> List[Dict[str, str]]:
    channels: List[Dict[str, str]] = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            attrs = {}
            matches = re.findall(r'(\w[\w-]*)="([^"]*)"', line)
            for key, value in matches:
                attrs[key] = value
            name_part = line.split(",", 1)
            name = name_part[1].strip() if len(name_part) > 1 else "Unknown"
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                channels.append(
                    {
                        "name": name,
                        "url": url,
                        "logo_url": attrs.get("tvg-logo"),
                        "category": attrs.get("group-title"),
                        "country": attrs.get("tvg-country"),
                        "language": attrs.get("tvg-language"),
                    }
                )
                i += 2
                continue
        i += 1
    return channels

