#!/usr/bin/env python3
"""
Record relative Warthog transforms from Gazebo model poses to CSV.
Assumes that there is a running Gazebo Ignition simulation and bridge to ROS2.
Details on bridge can be found in the platform launch file under the clearpath directory.
"""

import csv
import os
from pathlib import Path
import time
from typing import Optional

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from scipy.spatial.transform import Rotation as R
from tf2_msgs.msg import TFMessage

class WarthogRelativeTransformRecorder(Node):
    """Subscribe to Gazebo ModelStates and save relative transforms."""

    def __init__(self) -> None:
        super().__init__("warthog_relative_transform_recorder")

        self.declare_parameter("map", Parameter.Type.STRING)
        self.declare_parameter("model_name", Parameter.Type.STRING)
        self.declare_parameter("output_filename", "relative_transforms.csv")
        self.declare_parameter("sampling_interval", 0.2)
        # self.declare_parameter("tf_topic", "/w200_0066/tf")
        # self.declare_parameter("parent_frame_id", "parking_world")
        # self.declare_parameter("child_frame_id", "w200_0066/robot")

        # Check map directory exists
        map_param = self.get_parameter("map")
        if map_param is None or map_param.value == "":
            raise RuntimeError("Required parameter 'map' must be set to a non-empty string")
        virtr = os.environ["VIRTR"]
        map_path = Path(virtr) / "data" / map_param.value
        assert map_path.exists(), f"Map path does not exist: {map_path}"

        # Require a model name
        model_param = self.get_parameter("model_name")
        if model_param is None or model_param.value == "":
            raise RuntimeError("Required parameter 'model_name' must be set to a non-empty string")
        self.model_name = model_param.value

        # Set up output file path
        self.output_dir = os.path.expanduser(map_path / "paths")
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_filename = self.get_parameter("output_filename").value
        self.output_file = os.path.join(self.output_dir, self.output_filename)


        # Other parameters
        self.sampling_interval = float(self.get_parameter("sampling_interval").value)
        self.tf_topic = "/" + self.model_name + "/tf"
        self.parent_frame_id = map_param.value
        self.child_frame_id = self.model_name + "/robot"
        # self.tf_topic = str(self.get_parameter("tf_topic").value)
        # self.parent_frame_id = str(self.get_parameter("parent_frame_id").value)
        # self.child_frame_id = str(self.get_parameter("child_frame_id").value)

        self.initial_pose: Optional[np.ndarray] = None
        self.previous_pose: Optional[np.ndarray] = None
        self.last_timestamp: Optional[float] = None

        self.subscription = self.create_subscription(
            TFMessage,
            self.tf_topic,
            self.callback,
            10,
        )

        self.get_logger().info(
            f"Logging {self.model_name} relative transforms to {self.output_file}"
        )

    def pose_to_matrix(self, position, orientation):
        """Convert position and orientation (quaternion) to a 4x4 transformation matrix."""
        rotation = R.from_quat([orientation.x, orientation.y, orientation.z, orientation.w]).as_matrix()
        transform = np.eye(4)
        transform[:3, :3] = rotation
        transform[:3, 3] = [position.x, position.y, position.z]
        return transform

    def compute_relative_transform(self, current_matrix: np.ndarray, previous_matrix: np.ndarray) -> np.ndarray:
        """Compute the relative transformation matrix."""
        return np.linalg.inv(current_matrix) @ previous_matrix
        #return np.linalg.inv(previous_matrix) @ current_matrix

    def find_target_transform(self, msg: TFMessage):
        """Return the target transform in a TFMessage, or None."""
        for tf in msg.transforms:
            parent = tf.header.frame_id
            child = tf.child_frame_id
            if parent == self.parent_frame_id and child == self.child_frame_id:
                return tf
        return None

    def callback(self, msg: TFMessage) -> None:

        # Get the real-world epoch time
        timestamp = time.time()

        # Check if enough time has passed since the last message
        if self.last_timestamp is not None and (timestamp - self.last_timestamp) < self.sampling_interval:
            return  # Skip processing if the interval has not elapsed

        try:
            # Find the transform of the Warthog
            target_tf = self.find_target_transform(msg)

            if target_tf is None:
                # self.get_logger().warn(f"Transform from {self.parent_frame_id} to {self.child_frame_id} not found in TFMessage.", throttle_duration_sec=5.0)
                return

            # Convert the pose to a 4x4 transformation matrix
            current_matrix = self.pose_to_matrix(target_tf.transform.translation, target_tf.transform.rotation)

            # If this is the first message, save the absolute pose as the initial pose
            if self.initial_pose is None:
                #initial_pose = np.eye(4)
                self.initial_pose = current_matrix

                # Write the header and initial pose to the CSV file
                with open(self.output_file, "w", newline="") as csvfile:
                    csvwriter = csv.writer(csvfile)
                    header = ["timestamp"] + [f"m{i}{j}" for i in range(4) for j in range(4)]
                    csvwriter.writerow(header)
                    csvwriter.writerow([timestamp] + self.initial_pose.flatten().tolist())

            # If we have a previous pose, compute the relative transform
            if self.previous_pose is not None:
                relative_matrix = self.compute_relative_transform(current_matrix, self.previous_pose)
                relative_flat = relative_matrix.flatten()

                # Open the file in append mode and save the timestamp and relative transform
                with open(self.output_file, "a", newline="") as csvfile:
                    csvwriter = csv.writer(csvfile)
                    csvwriter.writerow([timestamp] + relative_flat.tolist())

            # Update the previous pose to the current matrix
            self.previous_pose = current_matrix

            # Update the last timestamp when we get a valid pose
            self.last_timestamp = timestamp

            return

        except ValueError:
            self.get_logger().warn(f"Transform from {self.parent_frame_id} to {self.child_frame_id} not found in TFMessage.", throttle_duration_sec=5.0)
            return

def main(args=None) -> None:
    rclpy.init(args=args)
    node = WarthogRelativeTransformRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()