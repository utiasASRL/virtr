from setuptools import find_packages, setup

package_name = 'relative_transform_recorder'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='elliot',
    maintainer_email='elliot.prestonkrebs@mail.utoronto.ca',
    description='Record relative transforms from Gazebo-bridged ROS2 TF messages during manual robot teleoperation in simulation.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        "console_scripts": [
            "save_path = relative_transform_recorder.save_path:main",
        ],
    },
)
