from utils import (
    read_video, save_video, measure_distance, draw_player_stats, convert_pixel_distance_to_meters
)
import constants
from trackers import PlayerTracker, BallTracker, PoseDetector
from court_line_detector import CourtLineDetector
from mini_court import MiniCourt
import cv2
import pandas as pd
from copy import deepcopy
import os



def main():
    # Ensure input and output directories exist
    input_video_path = "static/input_videos/input_video.mp4"
    output_video_path = "static/output_videos/input_video1.avi"
    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)

    # Read Video
    print("Reading video...")
    video_frames = read_video(input_video_path)

    # Detect Players and Ball
    player_tracker = PlayerTracker(model_path='yolov8x')
    ball_tracker = BallTracker(model_path='models/yolov5l6u.pt')
    pose_detector = PoseDetector(model_path='models/final_pose_model.pth')

    print("Detecting players and ball...")
    player_detections = player_tracker.detect_frames(
        video_frames, read_from_stub=True, stub_path="tracker_stubs/player_detections.pkl"
    )
    ball_detections = ball_tracker.detect_frames(
        video_frames, read_from_stub=True, stub_path="tracker_stubs/ball_detections.pkl"
    )
    ball_detections = ball_tracker.interpolate_ball_positions(ball_detections)

    # Court Line Detection
    print("Detecting court lines...")
    court_model_path = "models/keypoints_model.pth"
    court_line_detector = CourtLineDetector(court_model_path)
    court_keypoints = court_line_detector.predict(video_frames[0])

    # Filter players
    print("Filtering player detections...")
    player_detections = player_tracker.choose_and_filter_players(court_keypoints, player_detections)

    # Initialize Mini Court
    mini_court = MiniCourt(video_frames[0])

    # Detect ball shots
    ball_shot_frames = ball_tracker.get_ball_shot_frames(ball_detections)

    # Convert positions to mini court coordinates
    print("Converting positions to mini court coordinates...")
    player_mini_court_detections, ball_mini_court_detections = mini_court.convert_bounding_boxes_to_mini_court_coordinates(
        player_detections, ball_detections, court_keypoints
    )

    # Initialize player statistics data
    player_stats_data = [{
        'frame_num': 0,
        'player_1_number_of_shots': 0, 'player_1_total_shot_speed': 0, 'player_1_last_shot_speed': 0,
        'player_1_total_player_speed': 0, 'player_1_last_player_speed': 0,
        'player_2_number_of_shots': 0, 'player_2_total_shot_speed': 0, 'player_2_last_shot_speed': 0,
        'player_2_total_player_speed': 0, 'player_2_last_player_speed': 0,
        'player_1_pose_backhand': 0, 'player_1_pose_forehand': 0, 'player_1_pose_ready': 0, 'player_1_pose_serve': 0,
        'player_2_pose_backhand': 0, 'player_2_pose_forehand': 0, 'player_2_pose_ready': 0, 'player_2_pose_serve': 0
    }]
        
    print("Calculating player statistics...")
    for ball_shot_ind in range(len(ball_shot_frames) - 1):
        start_frame = ball_shot_frames[ball_shot_ind]
        end_frame = ball_shot_frames[ball_shot_ind + 1]
        ball_shot_time_in_seconds = (end_frame - start_frame) / 24  # Assuming 24fps

        # Measure ball distance and speed
        distance_covered_pixels = measure_distance(
            ball_mini_court_detections[start_frame][1], ball_mini_court_detections[end_frame][1]
        )
        distance_covered_meters = convert_pixel_distance_to_meters(
            distance_covered_pixels, constants.DOUBLE_LINE_WIDTH, mini_court.get_width_of_mini_court()
        )
        speed_of_ball_shot = (distance_covered_meters / ball_shot_time_in_seconds) * 3.6  # km/h

        # Identify the player who hit the ball
        player_positions = player_mini_court_detections[start_frame]
        player_shot_ball = min(
            player_positions.keys(),
            key=lambda pid: measure_distance(player_positions[pid], ball_mini_court_detections[start_frame][1])
        )
        # Copy the previous stats to keep a running total.
        current_stats = deepcopy(player_stats_data[-1])
        current_stats['frame_num'] = start_frame

        player_frame = video_frames[start_frame].copy()
        for player_id, bbox in player_detections[start_frame].items():
            # Predict keypoints and pose class
            keypoints, pose_class = pose_detector.crop_and_predict_pose(player_frame, bbox)
            player_frame = pose_detector.draw_pose(player_frame, bbox, keypoints, pose_class)

            # Print for debugging purposes
            pose_label = ["Backhand", "Forehand", "Ready", "Serve"][pose_class]
            print(f"Player {player_id} detected with pose: {pose_label}")

            # Ensure stats are updated correctly
            stat_key = f'player_{player_id}_pose_{pose_label.lower()}'

            if stat_key in current_stats:
                current_stats[stat_key] += 1
            else:
                print(f"Invalid stat key: {stat_key}")  # Debugging message

        # Ensure the modified frame is saved back to the video frames
        video_frames[start_frame] = player_frame

        # Update statistics for this frame
        player_stats_data.append(current_stats)
        # Calculate opponent speed
        opponent_id = 1 if player_shot_ball == 2 else 2
        opponent_distance_pixels = measure_distance(
            player_mini_court_detections[start_frame][opponent_id],
            player_mini_court_detections[end_frame][opponent_id]
        )
        opponent_distance_meters = convert_pixel_distance_to_meters(
            opponent_distance_pixels, constants.DOUBLE_LINE_WIDTH, mini_court.get_width_of_mini_court()
        )
        opponent_speed = (opponent_distance_meters / ball_shot_time_in_seconds) * 3.6  # km/h

        # Update player stats
        current_stats = deepcopy(player_stats_data[-1])
        current_stats['frame_num'] = start_frame
        current_stats[f'player_{player_shot_ball}_number_of_shots'] += 1
        current_stats[f'player_{player_shot_ball}_total_shot_speed'] += speed_of_ball_shot
        current_stats[f'player_{player_shot_ball}_last_shot_speed'] = speed_of_ball_shot
        current_stats[f'player_{opponent_id}_total_player_speed'] += opponent_speed
        current_stats[f'player_{opponent_id}_last_player_speed'] = opponent_speed
        player_stats_data.append(current_stats)

    # Create a DataFrame for player stats
    stats_df = pd.DataFrame(player_stats_data)
    frames_df = pd.DataFrame({'frame_num': range(len(video_frames))})
    stats_df = pd.merge(frames_df, stats_df, on='frame_num', how='left').ffill()
    
    # Calculate average speeds
    stats_df['player_1_average_shot_speed'] = stats_df['player_1_total_shot_speed'] / stats_df['player_1_number_of_shots']
    stats_df['player_2_average_shot_speed'] = stats_df['player_2_total_shot_speed'] / stats_df['player_2_number_of_shots']
    stats_df['player_1_average_player_speed'] = stats_df['player_1_total_player_speed'] / stats_df['player_2_number_of_shots']
    stats_df['player_2_average_player_speed'] = stats_df['player_2_total_player_speed'] / stats_df['player_1_number_of_shots']

    print(stats_df[['frame_num', 
                'player_1_pose_backhand', 'player_1_pose_forehand',
                'player_1_pose_ready', 'player_1_pose_serve']].head())
    # Draw bounding boxes, keypoints, and stats on the video frames
    print("Generating output video...")
    output_frames = pose_detector.draw_poses(video_frames, player_detections, {})
    output_frames = player_tracker.draw_bboxes(video_frames, player_detections)
    output_frames = ball_tracker.draw_bboxes(output_frames, ball_detections)
    output_frames = court_line_detector.draw_keypoints_on_video(output_frames, court_keypoints)
    output_frames = mini_court.draw_mini_court(output_frames)
    output_frames = mini_court.draw_points_on_mini_court(output_frames, player_mini_court_detections)
    output_frames = mini_court.draw_points_on_mini_court(output_frames, ball_mini_court_detections, color=(0, 255, 255))
    output_frames = draw_player_stats(output_frames, stats_df)

    # Add frame numbers to the video
    for i, frame in enumerate(output_frames):
        cv2.putText(frame, f"Frame: {i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Save the output video
    save_video(output_frames, output_video_path)
    print(f"Video saved at {output_video_path}")

if __name__ == "__main__":
    main()
