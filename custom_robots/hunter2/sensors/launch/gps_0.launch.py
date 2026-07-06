from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    launch_arg_prefix = DeclareLaunchArgument(
        'prefix',
        default_value='',
        description='')

    prefix = LaunchConfiguration('prefix')

    # Nodes
    node_gps_0_gz_bridge = Node(
        name='gps_0_gz_bridge',
        executable='parameter_bridge',
        package='ros_gz_bridge',
        namespace='hunter2/sensors/',
        output='screen',
        parameters=
            [
                {
                    'use_sim_time': True
                    ,
                    'config_file': '/home/hunter/ASRL/vtr3/virtr/custom_robots/hunter2/sensors/config/gps_0.yaml'
                    ,
                }
                ,
            ]
        ,
    )

    node_gps_0_static_tf = Node(
        name='gps_0_static_tf',
        executable='static_transform_publisher',
        package='tf2_ros',
        namespace='hunter2',
        output='screen',
        arguments=
            [
                '--frame-id'
                ,
                'gps_0_link'
                ,
                '--child-frame-id'
                ,
                'hunter2/robot/base_link/gps_0'
                ,
            ]
        ,
        remappings=
            [
                (
                    '/tf'
                    ,
                    'tf'
                )
                ,
                (
                    '/tf_static'
                    ,
                    'tf_static'
                )
                ,
            ]
        ,
        parameters=
            [
                {
                    'use_sim_time': True
                    ,
                }
                ,
            ]
        ,
    )

    # Create LaunchDescription
    ld = LaunchDescription()
    ld.add_action(launch_arg_prefix)
    ld.add_action(node_gps_0_gz_bridge)
    ld.add_action(node_gps_0_static_tf)
    return ld
