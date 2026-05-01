import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import exifread

class PhotoPoint:
    def __init__(self, filepath: str, lat: float, lon: float,
                 timestamp: datetime, url: Optional[str] = None):
        self.filepath = filepath
        self.lat = lat
        self.lon = lon
        self.timestamp = timestamp
        self.url = url or filepath

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
    except:
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

        if 'EXIF DateTimeOriginal' in tags:
            date_str = str(tags['EXIF DateTimeOriginal'].values)
            return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
        return None
    except:
        return None

def match_photos_to_track(photo_dir: str, track_start_time: datetime,
                          track_points: list, time_offset: float = 0) -> List[Dict]:
    photos = []
    photo_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.tiff'}

    if hasattr(track_start_time, 'to_pydatetime'):
        track_start_time = track_start_time.to_pydatetime()

    for filepath in Path(photo_dir).glob('*'):
        if filepath.suffix.lower() in photo_extensions:
            timestamp = extract_timestamp_from_photo(str(filepath))
            gps = extract_gps_from_photo(str(filepath))

            if timestamp and gps:
                time_offset_sec = (timestamp - track_start_time).total_seconds() + time_offset
                if time_offset_sec >= 0:
                    photos.append({
                        'filepath': str(filepath),
                        'lat': gps[0],
                        'lon': gps[1],
                        'timestamp': timestamp,
                        'timeOffset': time_offset_sec,
                        'url': str(filepath)
                    })

    return sorted(photos, key=lambda x: x['timeOffset'])
