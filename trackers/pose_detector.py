import torch
import cv2
import numpy as np
from torchvision import transforms, models
from PIL import Image

class PoseDetector:
    def __init__(self, model_path):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self._load_model(model_path)
        self.model.eval()

        self.pose_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

    def _load_model(self, model_path):
        model = PoseEstimationModel(num_keypoints=18, num_classes=4)
        model.load_state_dict(torch.load(model_path, map_location=self.device))
        model.to(self.device)
        return model

    def crop_and_predict_pose(self, frame, bbox):
        """Crop the player from the frame and predict keypoints and pose class."""
        x1, y1, x2, y2 = map(int, bbox)
        cropped_frame = frame[y1:y2, x1:x2]

        # Convert to RGB and apply transformations
        image = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
        image = self.pose_transform(Image.fromarray(image)).unsqueeze(0).to(self.device)

        # Perform inference
        with torch.no_grad():
            keypoints, class_logits = self.model(image)
            _, predicted_class = torch.max(class_logits, 1)

        # Convert keypoints to numpy and adjust scaling
        keypoints = keypoints.squeeze(0).cpu().numpy()

        # Scale keypoints back to original bbox size
        keypoints[:, 0] = keypoints[:, 0] * (x2 - x1) / 224 + x1  # Scale X
        keypoints[:, 1] = keypoints[:, 1] * (y2 - y1) / 224 + y1  # Scale Y

        predicted_class = predicted_class.item()

        return keypoints, predicted_class


    def draw_poses(self, video_frames, player_detections, pose_predictions):
        output_frames = []

        for frame, player_dict in zip(video_frames, player_detections):
            for player_id, bbox in player_dict.items():
                if player_id in pose_predictions:
                    keypoints, pose_class = pose_predictions[player_id]

                    # Ensure keypoints are valid and correctly formatted
                    if isinstance(keypoints, np.ndarray) and keypoints.shape == (18, 2):
                        for x, y in keypoints:
                            if 0 <= x < frame.shape[1] and 0 <= y < frame.shape[0]:  # Check bounds
                                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

                        x1, y1, _, _ = map(int, bbox)
                        pose_label = ["Backhand", "Forehand", "Ready", "Serve"][pose_class]
                        cv2.putText(frame, f"{pose_label}", (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    else:
                        print(f"Invalid keypoints for player {player_id}: {keypoints}")

            output_frames.append(frame)

        return output_frames
    
    def draw_pose(self, frame, bbox, keypoints, pose_class):
        """Draw keypoints and pose label on the player in the frame."""
        # Ensure bbox values are integers
        x1, y1, x2, y2 = map(int, bbox)

        # Draw keypoints on the player
        for (x, y) in keypoints:
            if 0 <= int(x) < frame.shape[1] and 0 <= int(y) < frame.shape[0]:  # Check if keypoints are within bounds
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)  # Draw green circle for keypoint

        # Draw the pose label above the bounding box
        pose_label = ["Backhand", "Forehand", "Ready", "Serve"][pose_class]
        cv2.putText(frame, f"{pose_label}", (x1, y1 - 10),  # Use x1, y1 as origin
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return frame  # Ensure the modified frame is returned

class PoseEstimationModel(torch.nn.Module):
    def __init__(self, num_keypoints=18, num_classes=4):
        super(PoseEstimationModel, self).__init__()
        # Use ResNet-18 as backbone
        self.backbone = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        num_features = self.backbone.fc.in_features

        # Replace the original fully connected layer with identity
        self.backbone.fc = torch.nn.Identity()

        # Define the keypoint and classification heads
        self.keypoint_head = torch.nn.Linear(num_features, num_keypoints * 2)
        self.classification_head = torch.nn.Linear(num_features, num_classes)

    def forward(self, x):
        features = self.backbone(x)  # Extract features
        keypoints = self.keypoint_head(features).view(-1, 18, 2)  # (batch, 18, 2)
        class_logits = self.classification_head(features)  # (batch, num_classes)
        return keypoints, class_logits
