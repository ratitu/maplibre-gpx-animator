import gpxpy
import gpxpy.gpx
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pandas as pd

class GPXTrackPoint:
    def __init__(self, lat: float, lon: float, elevation: Optional[float] = None,
                 time: Optional[datetime] = None, heart_rate: Optional[int] = None):
        self.lat = lat
        self.lon = lon
        self.elevation = elevation
        self.time = time
        self.heart_rate = heart_rate

class GPXTrackSegment:
    def __init__(self, points: List[GPXTrackPoint]):
        self.points = points

class GPXTrack:
    def __init__(self, name: str, segments: List[GPXTrackSegment]):
        self.name = name
        self.segments = segments

def parse_gpx_file(gpx_path: str) -> List[GPXTrack]:
    with open(gpx_path, 'r', encoding='utf-8') as f:
        gpx = gpxpy.parse(f)

    tracks = []
    for track in gpx.tracks:
        track_segments = []
        for segment in track.segments:
            points = []
            for point in segment.points:
                hr = None
                if point.extensions:
                    for ext in point.extensions:
                        if 'hr' in ext.tag or 'heartrate' in ext.tag.lower():
                            try:
                                hr = int(ext.text)
                            except:
                                pass

                points.append(GPXTrackPoint(
                    lat=point.latitude,
                    lon=point.longitude,
                    elevation=point.elevation,
                    time=point.time,
                    heart_rate=hr
                ))
            track_segments.append(GPXTrackSegment(points))
        tracks.append(GPXTrack(track.name or "Unnamed Track", track_segments))
    return tracks

def get_track_bounds(tracks: List[GPXTrack]) -> Tuple[float, float, float, float]:
    min_lat, max_lat = 90, -90
    min_lon, max_lon = 180, -180

    for track in tracks:
        for segment in track.segments:
            for point in segment.points:
                min_lat = min(min_lat, point.lat)
                max_lat = max(max_lat, point.lat)
                min_lon = min(min_lon, point.lon)
                max_lon = max(max_lon, point.lon)

    return min_lat, min_lon, max_lat, max_lon

def tracks_to_dataframe(tracks: List[GPXTrack]) -> pd.DataFrame:
    data = []
    for track in tracks:
        for seg_idx, segment in enumerate(track.segments):
            for pt_idx, point in enumerate(segment.points):
                data.append({
                    'track_name': track.name,
                    'segment_idx': seg_idx,
                    'point_idx': pt_idx,
                    'lat': point.lat,
                    'lon': point.lon,
                    'elevation': point.elevation,
                    'time': point.time,
                    'heart_rate': point.heart_rate
                })
    return pd.DataFrame(data)
