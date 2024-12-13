import cv2
import os

def read_video(video_path):
    """Reads a video and returns a list of frames."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Unable to open video file: {video_path}")
    
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    
    if not frames:
        raise ValueError("No frames found in the video.")
    
    return frames

def save_video(output_video_frames, output_video_path, fps=24):
    """Saves a list of frames as a video."""
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)

    # Get the dimensions from the first frame
    height, width, _ = output_video_frames[0].shape

    # Use a reliable codec for compatibility
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')

    # Initialize VideoWriter
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    # Write each frame to the output video
    for frame in output_video_frames:
        out.write(frame)

    out.release()

    if not os.path.isfile(output_video_path):
        raise ValueError(f"Failed to save video at: {output_video_path}")

