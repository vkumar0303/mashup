import os
import yt_dlp
import time
from moviepy.editor import VideoFileClip
import zipfile
from pydub import AudioSegment
from flask import Flask, request, send_file, render_template, redirect, url_for, jsonify

app = Flask(__name__)

# Function to download videos using yt-dlp
def download_videos(singer, number_of_videos):
    download_path = os.getcwd()

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'quiet': True,
    }

    search_url = f"ytsearch{number_of_videos}:{singer}"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(search_url, download=True)
            return len(result['entries']) if 'entries' in result else 0
        except Exception as e:
            print(f"Error: {e}")
            return 0

# Function to convert video to audio
def convert_video_to_audio(video_file_path):
    audio_file_path = os.path.splitext(video_file_path)[0] + ".mp3"
    try:
        video_clip = VideoFileClip(video_file_path)
        audio_clip = video_clip.audio
        audio_clip.write_audiofile(audio_file_path)
        audio_clip.close()
        video_clip.close()
        os.remove(video_file_path)
        return audio_file_path
    except Exception as e:
        print(f"Error converting {video_file_path} to audio: {e}")
        return None

# Function to cut a segment from an audio file
def cut_audio_segment(audio_file_path, start_time=20000, duration=10):
    try:
        audio = AudioSegment.from_file(audio_file_path)
        end_time = start_time + duration * 1000
        cut_audio = audio[start_time:end_time]
        cut_audio.export(audio_file_path, format="mp3")
        print(f"Cut audio segment: {audio_file_path} from {start_time / 1000}s to {end_time / 1000}s")
    except Exception as e:
        print(f"Error cutting audio {audio_file_path}: {e}")

# Function to merge multiple audio files into one
def merge_audio_files(audio_file_paths, output_path='static/merged_audio.mp3'):
    combined = AudioSegment.empty()
    for file_path in audio_file_paths:
        try:
            audio = AudioSegment.from_file(file_path)
            combined += audio
            print(f"Merged file: {file_path}")
        except Exception as e:
            print(f"Error merging file {file_path}: {e}")
    combined.export(output_path, format="mp3")
    print(f"Merged audio file created at: {output_path}")
    return output_path

# Function to zip the merged audio file
def zip_audio_file(file_path, zip_name='static/merged_audio.zip'):
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        zipf.write(file_path, os.path.basename(file_path))
    print(f"Zipped file created at: {zip_name}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_mashup', methods=['POST'])
def generate_mashup():
    singer = request.form.get('singer')
    number_of_videos = request.form.get('number_of_videos')
    duration = request.form.get('duration', 10)

    if not singer or not number_of_videos:
        return "Please provide both singer name and number of videos.", 400

    try:
        number_of_videos = int(number_of_videos)
        duration = int(duration)
    except ValueError:
        return "Please provide valid numbers for the number of videos and duration.", 400

    num_downloaded = 0
    for _ in range(3):
        num_downloaded = download_videos(singer, number_of_videos)
        if num_downloaded > 0:
            break
        time.sleep(5)

    print(f"Downloaded {num_downloaded} videos of {singer} to the current directory.")

    download_path = os.getcwd()
    audio_file_paths = []
    for file_name in os.listdir(download_path):
        if file_name.endswith('.mp4'):
            video_file_path = os.path.join(download_path, file_name)
            audio_file_path = convert_video_to_audio(video_file_path)
            if audio_file_path:
                cut_audio_segment(audio_file_path, start_time=20 * 1000, duration=duration)
                audio_file_paths.append(audio_file_path)

    if audio_file_paths:
        merged_audio_path = merge_audio_files(audio_file_paths)

        # Only zip if the merged audio file was created successfully
        if merged_audio_path and os.path.exists(merged_audio_path):
            zip_audio_file(merged_audio_path)

            # Return the URL of the zipped file in JSON format
            zip_url = url_for('download_zip', _external=True)  # Get the full URL
            return jsonify({'zip_url': zip_url})

    return jsonify({'error': "No audio files processed."}), 500

@app.route('/download_zip')
def download_zip():
    zip_path = os.path.join(os.getcwd(), 'static', 'merged_audio.zip')
    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
