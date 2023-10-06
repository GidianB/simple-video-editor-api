from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
import tempfile
import requests
import cv2
import numpy as np
from moviepy.editor import *
import time
import io

app = FastAPI()

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 1
FONT_THICKNESS = 2
COLOR = (255, 255, 255)
LINE_HEIGHT = 40  # Adjust this value to change the spacing between lines


def wrap_text(text, max_width, font, font_scale, font_thickness):
    """
    Wrap text to fit within the specified width.
    """
    wrapped_lines = []
    words = text.split()
    while words:
        line = ''
        while words and cv2.getTextSize(line + words[0], font, font_scale, font_thickness)[0][0] <= max_width:
            line += (words.pop(0) + ' ')
        wrapped_lines.append(line)
    return wrapped_lines

def draw_centered_text(image, text):
    """
    Draw the specified text centered on the image.
    """
    image_height, image_width, _ = image.shape

    # Split the text into lines that fit within the width of the image
    wrapped_text = wrap_text(text, image_width * 0.8, FONT, FONT_SCALE, FONT_THICKNESS)

    # Calculate the starting y-coordinate to center the text block vertically
    (text_width, text_height), _ = cv2.getTextSize("Test", FONT, FONT_SCALE, FONT_THICKNESS)
    total_text_height = len(wrapped_text) * text_height + (len(wrapped_text) - 1) * LINE_HEIGHT
    y_start = (image_height - total_text_height) // 2 + text_height

    # Calculate the width of each line of text
    line_widths = [cv2.getTextSize(line, FONT, FONT_SCALE, FONT_THICKNESS)[0][0] for line in wrapped_text]

    # Draw each line of text centered on the image
    for idx, line in enumerate(wrapped_text):
        y = y_start + (idx * (text_height + LINE_HEIGHT))
        x = (image_width - line_widths[idx]) // 2
        cv2.putText(image, line, (x, y), FONT, FONT_SCALE, COLOR, FONT_THICKNESS, lineType=cv2.LINE_AA)

    return image

def get_video_from_url(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Unable to fetch the video from the provided URL")
    
    video_bytes = response.content
    video_stream = io.BytesIO(video_bytes)
    return video_stream


def add_text_frame_to_video_and_concatenate(video_stream, text, duration_seconds):
    # Convert the video stream into a temporary file
    temp_filename = tempfile.mktemp(suffix=".mp4")
    with open(temp_filename, "wb") as f:
        f.write(video_stream.read())

    # Load the video using moviepy
    video_clip = VideoFileClip(temp_filename)

    # Create a blank black frame with the same resolution as the video
    frame = np.zeros((video_clip.size[1], video_clip.size[0], 3), dtype=np.uint8)
    frame_with_text = draw_centered_text(frame, text)

    # Convert the image frame back to a moviepy Clip
    text_clip = ImageSequenceClip([frame_with_text], durations=[duration_seconds])
    final_clip = concatenate_videoclips([video_clip, text_clip])

    # Save the modified video to a temporary file
    output_filename = tempfile.mktemp(suffix=".mp4")
    final_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac")

    # Read the output video into a stream
    with open(output_filename, "rb") as f:
        output_stream = io.BytesIO(f.read())

    # Cleanup temporary files
    time.sleep(1)
    os.remove(temp_filename)
    os.remove(output_filename)

    return output_stream

@app.post("/addStaticTextFrame/")
async def add_static_text_frame(fileUrl: str, text: str, duration_seconds: int = 5):
    video_stream = get_video_from_url(fileUrl)
    output_stream = add_text_frame_to_video_and_concatenate(video_stream, text, duration_seconds)

    return StreamingResponse(output_stream, media_type="video/mp4")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
