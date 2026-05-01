import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import exifread
import base64
import imghdr

def extract_gps_from_photo(photo_path: str) -> Optional[tuple]:
    try:
        with open(photo_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)

        if 'GPS GPSLatitude' not in tags or 'GPS GPSLongitude' not in tags:
            return None

        lat = _convert_to_degrees(tags['GPS GPSLatitude'])
        lon = _convert_to_degrees(tags['GPS GPSLongitude'])

        if 'GPS GPSLatitudeRef' in tags and tags['GPS GPSLatitudeRef'].values[0] == 'S':
            lat = -lat
        if 'GPS GPSLongitudeRef' in tags and tags['GPS GPSLongitudeRef'].values[0] == 'W':
            lon = -lon

        return lat, lon
    except Exception:
        return None

def _convert_to_degrees(value):
    d = float(value.values[0].num) / float(value.values[0].den)
    m = float(value.values[1].num) / float(value.values[1].den)
    s = float(value.values[2].num) / float(value.values[2].den)
    return d + (m / 60.0) + (s / 3600.0)

def extract_timestamp_from_photo(photo_path: str) -> Optional[datetime]:
    try:
        with open(photo_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)

        if 'GPS GPSDateStamp' in tags and 'GPS GPSTimeStamp' in tags:
            date_str = str(tags['GPS GPSDateStamp'].values)
            time_tag = tags['GPS GPSTimeStamp'].values

            hour = 0
            minute = 0
            second = 0
            if len(time_tag) > 0:
                hour = int(time_tag[0].num) if hasattr(time_tag[0], 'num') else int(time_tag[0])
            if len(time_tag) > 1:
                minute = int(time_tag[1].num) if hasattr(time_tag[1], 'num') else int(time_tag[1])
            if len(time_tag) > 2:
                second = int(time_tag[2].num) if hasattr(time_tag[2], 'num') else int(time_tag[2])

            return datetime.strptime(f"{date_str} {hour:02d}:{minute:02d}:{second:02d}", '%Y:%m:%d %H:%M:%S')

        return None
    except Exception:
        return None

def match_photos_to_track(photo_dir: str, track_points: list) -> List[Dict]:
    photos = []
    photo_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.tiff'}

    for filepath in Path(photo_dir).glob('*'):
        if filepath.suffix.lower() in photo_extensions:
            try:
                timestamp = extract_timestamp_from_photo(str(filepath))
                gps = extract_gps_from_photo(str(filepath))

                if gps:
                    try:
                        with open(str(filepath), 'rb') as img_file:
                            img_data = base64.b64encode(img_file.read()).decode('utf-8')
                            img_type = imghdr.what(str(filepath)) or 'jpeg'
                            base64_url = f"data:image/{img_type};base64,{img_data}"
                    except Exception:
                        base64_url = 'file://' + str(filepath.absolute())

                    photos.append({
                        'filepath': str(filepath),
                        'lat': gps[0],
                        'lon': gps[1],
                        'timestamp': timestamp.isoformat() if timestamp else None,
                        'url': base64_url
                    })
            except Exception:
                continue

    return photos
