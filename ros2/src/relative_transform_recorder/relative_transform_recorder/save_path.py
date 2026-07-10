#!/usr/bin/env python3
"""
Record relative transforms from Gazebo model poses to CSV.
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

class RelativeTransformRecorder(Node):
    """
    Subscribe to Gazebo ModelStates bridged to ROS2 and save relative transforms.

    Outputs a CSV file with flattened relative transforms:
        T_{w_{sim}_r{0}}, T_{r_{1}_r{0}}, T_{r_{2}_r{1}}, ..., T_{r_{n}_r{n-1}}

    Note the first transform is the absolute pose of the robot in the simulated world frame, and subsequent transforms are relative to the previous pose.

    Optionally outputs a CSV file with georeferenced transforms:
        T_{w_{geo}_r{0}}, T_{w_{geo}_r{1}}, ..., T_{w_{geo}_r{n}}
    """

    def __init__(self) -> None:
        super().__init__("relative_transform_recorder")

        self.declare_parameter("map", Parameter.Type.STRING)
        self.declare_parameter("model_name", Parameter.Type.STRING)
        self.declare_parameter("relative_tf_filename", "relative_transforms.csv")
        self.declare_parameter("geo_tf_filename", "georeferenced_transforms.csv")
        self.declare_parameter("sampling_interval", 0.2)
        self.declare_parameter("save_georeferenced_transforms", False)

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
        self.relative_tf_filename = self.get_parameter("relative_tf_filename").value
        self.relative_tf_file = os.path.join(self.output_dir, self.relative_tf_filename)

        self.save_georeferenced_transforms = self.get_parameter("save_georeferenced_transforms").value
        if self.save_georeferenced_transforms:
            # Get georeferenced offset from the map directory
            offset_file_path = os.path.join(map_path, "offset.xyz")
            if not os.path.exists(offset_file_path):
                offset_file_path = os.path.join(map_path, "offset.txt")
            assert os.path.exists(offset_file_path), f"Offset file not found in {map_path}, must include offset.xyz or offset.txt to save georeferenced transforms"
            
            offset = np.loadtxt(offset_file_path).reshape(-1)
            if offset.size != 3:
                raise ValueError(f"Expected exactly 3 offset values in {offset_file_path}, got shape {offset.shape}")
            
            self.T_geo_sim = np.eye(4)
            self.T_geo_sim[:3, 3] = offset

            # Set up georeferenced output file path
            self.geo_tf_filename = self.get_parameter("geo_tf_filename").value
            self.geo_tf_file = os.path.join(self.output_dir, self.geo_tf_filename)

        # Other parameters
        self.sampling_interval = float(self.get_parameter("sampling_interval").value)

        # Ex. "/w200_0066/tf"
        self.tf_topic = "/" + self.model_name + "/tf"

        # Ex. "dome"
        self.parent_frame_id = map_param.value

        # Ex. "w200_0066/robot"
        self.child_frame_id = self.model_name + "/robot"

        self.initial_pose: Optional[np.ndarray] = None
        self.previous_pose: Optional[np.ndarray] = None
        self.last_timestamp: Optional[float] = None

        self.subscription = self.create_subscription(
            TFMessage,
            self.tf_topic,
            self.callback,
            10,
        )

        if self.save_georeferenced_transforms:
            self.get_logger().info(f"Logging {self.model_name} relative transforms to {self.relative_tf_file} and georeferenced transforms to {self.geo_tf_file}")
        else:
            self.get_logger().info(f"Logging {self.model_name} relative transforms to {self.relative_tf_file}")

    def pose_to_matrix(self, position, orientation):
        """Convert position and orientation (quaternion) to a 4x4 transformation matrix."""
        rotation = R.from_quat([orientation.x, orientation.y, orientation.z, orientation.w]).as_matrix()
        transform = np.eye(4)
        transform[:3, :3] = rotation
        transform[:3, 3] = [position.x, position.y, position.z]
        return transform

    def compute_relative_transform(self, current_matrix: np.ndarray, previous_matrix: np.ndarray) -> np.ndarray:
        """
        Compute the relative transformation matrix.
        Transforms are recorded in the world frame: T_{w_{sim}_r}
        The desired format is a series of transforms T_{r_{k+1}_r_{k}} = (T_{w_{sim}_r_{k+1}})^{-1} * T_{w_{sim}_r_{k}}
        """
        return np.linalg.inv(current_matrix) @ previous_matrix
    
    def compute_georeferenced_transform(self, current_matrix: np.ndarray, offset_matrix: np.ndarray) -> np.ndarray:
        """
        Compute the georeferenced transformation matrix.
        current_matrix is the current pose of the robot in the world frame: T_{w_{sim}_r}
        offset_matrix is the offset from the simulated origin to the georeferenced world frame: T_{w_{geo}_w_{sim}}
        The desired format is T_{w_{geo}_r} = T_{w_{geo}_w_{sim}} * T_{w_{sim}_r}
        """
        return offset_matrix @ current_matrix

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
            # Find the transform of the robot
            target_tf = self.find_target_transform(msg)

            if target_tf is None:
                # self.get_logger().warn(f"Transform from {self.parent_frame_id} to {self.child_frame_id} not found in TFMessage.", throttle_duration_sec=5.0)
                return

            # Convert the pose to a 4x4 transformation matrix. Gazebo will publish the pose of the robot in the world frame, so this transform will be T_w_r
            current_matrix = self.pose_to_matrix(target_tf.transform.translation, target_tf.transform.rotation)

            # If this is the first message, save the absolute pose as the initial pose
            if self.initial_pose is None:
                #initial_pose = np.eye(4)
                self.initial_pose = current_matrix

                # Write the header and initial pose to the CSV file
                with open(self.relative_tf_file, "w", newline="") as csvfile:
                    csvwriter = csv.writer(csvfile)
                    header = ["timestamp"] + [f"m{i}{j}" for i in range(4) for j in range(4)]
                    csvwriter.writerow(header)
                    csvwriter.writerow([timestamp] + self.initial_pose.flatten().tolist())


                if self.save_georeferenced_transforms:
                    # Get georeferenced transform for the initial pose
                    T_geo_pose = self.compute_georeferenced_transform(current_matrix, self.T_geo_sim)

                    # Write the header and initial georeferenced pose to the CSV file
                    with open(self.geo_tf_file, "w", newline="") as csvfile:
                        csvwriter = csv.writer(csvfile)
                        header = ["timestamp"] + [f"m{i}{j}" for i in range(4) for j in range(4)]
                        csvwriter.writerow(header)
                        csvwriter.writerow([timestamp] + T_geo_pose.flatten().tolist())


            # If we have a previous pose, compute the relative transform
            if self.previous_pose is not None:
                relative_matrix = self.compute_relative_transform(current_matrix, self.previous_pose)
                relative_flat = relative_matrix.flatten()

                # Open the file in append mode and save the timestamp and relative transform
                with open(self.relative_tf_file, "a", newline="") as csvfile:
                    csvwriter = csv.writer(csvfile)
                    csvwriter.writerow([timestamp] + relative_flat.tolist())

                if self.save_georeferenced_transforms:
                    # Get georeferenced transform for the current pose
                    T_geo_pose = self.compute_georeferenced_transform(current_matrix, self.T_geo_sim)

                    # Open the file in append mode and save the timestamp and georeferenced transform
                    with open(self.geo_tf_file, "a", newline="") as csvfile:
                        csvwriter = csv.writer(csvfile)
                        csvwriter.writerow([timestamp] + T_geo_pose.flatten().tolist())

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
    node = RelativeTransformRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()