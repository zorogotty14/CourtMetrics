from ultralytics import YOLO 
import cv2
import pickle
import sys
sys.path.append('../')
from utils import measure_distance, get_center_of_bbox

class PlayerTracker:
    def __init__(self,model_path):
        self.model = YOLO(model_path)

    def choose_and_filter_players(self, court_keypoints, player_detections):
        player_detections_first_frame = player_detections[0]
        chosen_player = self.choose_players(court_keypoints, player_detections_first_frame)
        filtered_player_detections = []
        for player_dict in player_detections:
            filtered_player_dict = {track_id: bbox for track_id, bbox in player_dict.items() if track_id in chosen_player}
            filtered_player_detections.append(filtered_player_dict)
        return filtered_player_detections

    def choose_players(self, court_keypoints, player_dict):
        distances = []
        for track_id, bbox in player_dict.items():
            player_center = get_center_of_bbox(bbox)

            min_distance = float('inf')
            for i in range(0,len(court_keypoints),2):
                court_keypoint = (court_keypoints[i], court_keypoints[i+1])
                distance = measure_distance(player_center, court_keypoint)
                if distance < min_distance:
                    min_distance = distance
            distances.append((track_id, min_distance))
        
        # sorrt the distances in ascending order
        distances.sort(key = lambda x: x[1])
        # Choose the first 2 tracks
        chosen_players = [distances[0][0], distances[1][0]]
        return chosen_players


    def detect_frames(self,frames, read_from_stub=False, stub_path=None):
        player_detections = []

        if read_from_stub and stub_path is not None:
            with open(stub_path, 'rb') as f:
                player_detections = pickle.load(f)
            return player_detections

        for frame in frames:
            player_dict = self.detect_frame(frame)
            player_detections.append(player_dict)
        
        if stub_path is not None:
            with open(stub_path, 'wb') as f:
                pickle.dump(player_detections, f)
        
        return player_detections

    def detect_frame(self, frame):
        """Detect players and their keypoints in a single frame."""
        results = self.model.track(frame, persist=True)[0]
        id_name_dict = results.names

        player_dict = {}
        keypoints_dict = {}

        for box in results.boxes:
            track_id = int(box.id.tolist()[0])
            bbox = box.xyxy.tolist()[0]
            object_cls_id = box.cls.tolist()[0]
            object_cls_name = id_name_dict[object_cls_id]

            if object_cls_name == "person":
                player_dict[track_id] = bbox

                # Extract keypoints if available
                if hasattr(box, 'keypoints'):
                    keypoints_dict[track_id] = box.keypoints.cpu().numpy()

        return player_dict, keypoints_dict

    def draw_bboxes(self,video_frames, player_detections):
        output_video_frames = []

        for frame, (player_dict, keypoints_dict) in zip(video_frames, player_detections):
            for track_id, bbox in player_dict.items():
                x1, y1, x2, y2 = bbox

                # Draw the bounding box
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
                cv2.putText(frame, f"Player ID: {track_id}", 
                            (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

                # Draw skeleton if keypoints are available
                if track_id in keypoints_dict:
                    keypoints = keypoints_dict[track_id]
                    self.draw_skeleton(frame, keypoints)

            output_video_frames.append(frame)

        return output_video_frames
    

    def draw_skeleton(self, frame, keypoints):
        """
        Draws the skeleton on the provided frame using keypoints.
        
        Args:
            frame (np.ndarray): The video frame to draw on.
            keypoints (np.ndarray): Array of shape (N, 3), where N is the number of keypoints.
                                    Each keypoint is represented by (x, y, confidence).
        """
        # Define the pairs of keypoints that form the skeleton
        skeleton_pairs = [
            (0, 1), (1, 2), (2, 3), (3, 4),  # Head to shoulders
            (5, 6), (5, 7), (7, 9),          # Left arm
            (6, 8), (8, 10),                 # Right arm
            (11, 12), (11, 13), (13, 15),    # Left leg
            (12, 14), (14, 16)               # Right leg
        ]

        # Iterate over the skeleton pairs and draw lines between connected keypoints
        for start_idx, end_idx in skeleton_pairs:
            x1, y1, c1 = keypoints[start_idx]
            x2, y2, c2 = keypoints[end_idx]

            # Only draw if both keypoints are visible with confidence > 0.5
            if c1 > 0.5 and c2 > 0.5:
                # Draw the skeleton line between the two keypoints
                cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

        # Draw circles on each keypoint
        for x, y, c in keypoints:
            if c > 0.5:  # Only draw if confidence > 0.5
                cv2.circle(frame, (int(x), int(y)), 5, (255, 0, 0), -1)  # Blue dot for keypoints



    