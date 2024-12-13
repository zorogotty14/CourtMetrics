import numpy as np
import cv2

def draw_player_stats(output_video_frames, player_stats):
    """Draw player stats, including pose stats, on the video frames."""

    # Ensure that we don't exceed the available frames
    max_index = len(output_video_frames) - 1
    player_stats = player_stats.reset_index(drop=True)  # Reset index to align with frame numbers

    # Iterate through stats and apply them to frames (only if in range)
    for index, row in player_stats.iterrows():
        if index > max_index:
            print(f"Skipping frame {index} (out of range)")
            continue  # Skip stats if index exceeds frame range

        # Extract the relevant frame
        frame = output_video_frames[index]
        shapes = np.zeros_like(frame, np.uint8)

        # Define overlay area dimensions
        width, height = 350, 300  # Adjusted to fit additional stats
        start_x = frame.shape[1] - 400
        start_y = frame.shape[0] - 500
        end_x = start_x + width
        end_y = start_y + height

        # Create an overlay for stats display
        overlay = frame.copy()
        cv2.rectangle(overlay, (start_x, start_y), (end_x, end_y), (0, 0, 0), -1)
        alpha = 0.5
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        # Display shot and speed stats
        text = "     Player 1     Player 2"
        cv2.putText(frame, text, (start_x + 80, start_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.putText(frame, "Shot Speed", (start_x + 10, start_y + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        cv2.putText(frame, f"{row['player_1_last_shot_speed']:.1f} km/h    {row['player_2_last_shot_speed']:.1f} km/h",
                    (start_x + 130, start_y + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        cv2.putText(frame, "Player Speed", (start_x + 10, start_y + 120), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        cv2.putText(frame, f"{row['player_1_last_player_speed']:.1f} km/h    {row['player_2_last_player_speed']:.1f} km/h",
                    (start_x + 130, start_y + 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        cv2.putText(frame, "avg. S. Speed", (start_x + 10, start_y + 160), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        cv2.putText(frame, f"{row['player_1_average_shot_speed']:.1f} km/h    {row['player_2_average_shot_speed']:.1f} km/h",
                    (start_x + 130, start_y + 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        cv2.putText(frame, "avg. P. Speed", (start_x + 10, start_y + 200), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        cv2.putText(frame, f"{row['player_1_average_player_speed']:.1f} km/h    {row['player_2_average_player_speed']:.1f} km/h",
                    (start_x + 130, start_y + 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # Display pose stats for each player
        y_offset = 240
        player_1_pose_counts = {
            "Backhand": row['player_1_pose_backhand'],
            "Forehand": row['player_1_pose_forehand'],
            "Ready": row['player_1_pose_ready'],
            "Serve": row['player_1_pose_serve']
        }
        player_2_pose_counts = {
            "Backhand": row['player_2_pose_backhand'],
            "Forehand": row['player_2_pose_forehand'],
            "Ready": row['player_2_pose_ready'],
            "Serve": row['player_2_pose_serve']
        }

        for pose, count in player_1_pose_counts.items():
            cv2.putText(frame, f"{pose}: {count}", (start_x + 10, start_y + y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            y_offset += 20

        y_offset = 240
        for pose, count in player_2_pose_counts.items():
            cv2.putText(frame, f"{pose}: {count}", (start_x + 200, start_y + y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            y_offset += 20

    return output_video_frames
