import streamlit as st
import json
import tempfile
import os
from pathlib import Path
import shutil
import asyncio
import os
os.system("playwright install")

from gpx_parser import parse_gpx_file, get_track_bounds, tracks_to_dataframe
from video_generator import VideoGenerator
from photo_integration import match_photos_to_track

st.set_page_config(page_title="GPX Animation Generator", layout="wide")

def load_maplibre_template():
    template_path = Path(__file__).parent / "maplibre_template.html"
    with open(template_path, 'r') as f:
        return f.read()

def prepare_track_data(tracks, speed_factor=1.0):
    points = []
    for track in tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append({
                    'lat': point.lat,
                    'lon': point.lon,
                    'elevation': point.elevation,
                    'time': point.time.timestamp() if point.time else None,
                    'heart_rate': point.heart_rate
                })
    return points

def calculate_duration(tracks, speed_factor=1.0):
    total_points = sum(len(seg.points) for track in tracks for seg in track.segments)
    return (total_points / 30) / speed_factor

def get_center(bounds):
    min_lat, min_lon, max_lat, max_lon = bounds
    return [(min_lat + max_lat) / 2, (min_lon + max_lon) / 2]

def main():
    st.title("🎬 GPX Animation Video Generator")
    st.markdown("Upload GPX tracks and generate animated videos with MapLibre GL JS")

    with st.sidebar:
        st.header("Settings")

        st.subheader("Map Style")
        map_mode = st.selectbox("Map Mode", ["2D", "3D"])
        map_style = st.selectbox(
            "Map Style",
            ["https://demotiles.maplibre.org/style.json",
             "https://api.maptiler.com/maps/streets/style.json",
             "https://api.maptiler.com/maps/satellite/style.json"]
        )

        st.subheader("Animation")
        speed_factor = st.slider("Speed Factor", 0.5, 5.0, 1.0, 0.5)
        line_color = st.color_picker("Track Color", "#ff0000")
        line_width = st.slider("Track Width", 1, 10, 4)
        marker_size = st.slider("Marker Size", 4, 20, 8)
        marker_color = st.color_picker("Marker Color", "#ff0000")
        follow_track = st.checkbox("Follow Track", value=True)
        auto_play = st.checkbox("Auto Play", value=False)

        if map_mode == "3D":
            pitch = st.slider("Pitch", 0, 60, 45)
            bearing = st.slider("Bearing", 0, 360, 0)
        else:
            pitch = 0
            bearing = 0

        st.subheader("Video")
        fps = st.selectbox("FPS", [24, 30, 60], index=1)
        width = st.selectbox("Width", [1280, 1920, 3840], index=1)
        height = st.selectbox("Height", [720, 1080, 2160], index=1)

        st.subheader("Photos")
        photo_dir = st.text_input("Photo Directory (optional)")
        time_offset = st.number_input("Time Offset (seconds)", value=0.0)

    uploaded_file = st.file_uploader("Upload GPX File", type=['gpx'])

    if uploaded_file:
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.gpx', delete=False) as f:
            f.write(uploaded_file.getvalue())
            gpx_path = f.name

        tracks = parse_gpx_file(gpx_path)
        os.unlink(gpx_path)

        if not tracks:
            st.error("No tracks found in GPX file")
            return

        bounds = get_track_bounds(tracks)
        center = get_center(bounds)

        df = tracks_to_dataframe(tracks)
        st.success(f"Loaded {len(tracks)} track(s) with {len(df)} points")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Points", len(df))
        with col2:
            st.metric("Duration (calc)", f"{calculate_duration(tracks, speed_factor):.1f}s")

        with st.expander("Preview Track Data"):
            st.dataframe(df.head(100))

        if st.button("Generate Video", type="primary"):
            with st.spinner("Generating video..."):
                temp_dir = tempfile.mkdtemp()
                html_path = Path(temp_dir) / "animation.html"

                track_points = prepare_track_data(tracks)
                duration = calculate_duration(tracks, speed_factor)

                photos = []
                if photo_dir and Path(photo_dir).exists():
                    start_time = df['time'].min() if 'time' in df.columns and df['time'].notna().any() else None
                    if start_time:
                        photos = match_photos_to_track(photo_dir, start_time, track_points, time_offset)

                config = {
                    "trackPoints": track_points,
                    "duration": duration,
                    "mapStyle": map_style,
                    "center": center,
                    "zoom": 13,
                    "pitch": pitch,
                    "bearing": bearing,
                    "lineColor": line_color,
                    "lineWidth": line_width,
                    "markerSize": marker_size,
                    "markerColor": marker_color,
                    "followTrack": follow_track,
                    "autoPlay": auto_play,
                    "photos": photos if photos else None
                }

                template = load_maplibre_template()
                html_content = template.replace("__CONFIG__", json.dumps(config))
                html_path.write_text(html_content)

                output_path = Path(temp_dir) / "output.mp4"
                generator = VideoGenerator(temp_dir)
                try:
                    result = asyncio.run(
                        generator.generate_video(
                            str(html_path), duration, "output.mp4",
                            fps, width, height
                        )
                    )
                    st.video(result)
                    with open(result, 'rb') as f:
                        st.download_button("Download Video", f, "animation.mp4", "video/mp4")
                except Exception as e:
                    st.error(f"Error generating video: {str(e)}")
                    st.info("Make sure playwright and ffmpeg are installed: playwright install && apt install ffmpeg")
                finally:
                    generator.cleanup()

if __name__ == "__main__":
    main()
