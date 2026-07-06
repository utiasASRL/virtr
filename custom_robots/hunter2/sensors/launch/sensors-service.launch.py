from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    # Include Packages

    # Declare launch files
    launch_file_lidar3d_0 = '/home/hunter/ASRL/vtr3/virtr/custom_robots/hunter2/sensors/launch/lidar3d_0.launch.py'
    launch_file_camera_0 = '/home/hunter/ASRL/vtr3/virtr/custom_robots/hunter2/sensors/launch/camera_0.launch.py'
    launch_file_gps_0 = '/home/hunter/ASRL/vtr3/virtr/custom_robots/hunter2/sensors/launch/gps_0.launch.py'

    # Include launch files
    launch_lidar3d_0 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([launch_file_lidar3d_0]),
    )

    launch_camera_0 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([launch_file_camera_0]),
    )

    launch_gps_0 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([launch_file_gps_0]),
    )

    # Create LaunchDescription
    ld = LaunchDescription()
    ld.add_action(launch_lidar3d_0)
    ld.add_action(launch_camera_0)
    ld.add_action(launch_gps_0)
    return ld
