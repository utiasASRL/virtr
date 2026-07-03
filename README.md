## VirT&R Description
Virtual Teach & Repeat is a systematic pipeline to make virtual teach maps for VTR3 (https://github.com/utiasASRL/vtr3). Thus, it makes use of several programs and requires VTR3 to use.

This guide assumes that you have already set up and built VTR3. This version of VirTR is independent of any specific VTR3 branch, but it still depends on several VTR3 packages, including, but not limited to, vtr_common, vtr_pose_graph, and vtr_lidar. This dependency is handled by building a Docker container on top of the base VTR3 image, allowing VirTR to reuse VTR3 packages directly while avoiding redundant or diverging local copies.

## Download VirT&R
This package contains the vtr_virtual_teach C++ package for VTR3 and other custom scripts required to create virtual teach maps. Download it to your local filesystem in ${VTRROOT}.

Define the following environment variables. These can be added to your ~/.bashrc. Some other environment variables are set within the Docker file.
```Bash
export VIRTR=${VTRROOT}/virtr
export VIRTRWS=${VIRTR}/ros2
```

Clone this repository **and its submodules** into `VIRTR`:
```Bash
cd ${VTRROOT}
git clone --recurse-submodules -b ros2_port git@github.com:utiasASRL/virtr.git ${VIRTR}
```

## Docker Installation

Once VTR3 has been set up, the VirT&R pipeline can be installed. A separate Dockerfile is provided to install additional system dependencies on top of those included in the `vtr3` image.

Note that the run command includes the `__NV_PRIME_RENDER_OFFLOAD` and `__GLX_VENDOR_LIBRARY_NAME` environment variables. These are intended for systems with both an integrated GPU and a dedicated NVIDIA GPU, where Gazebo Ignition and Ogre2 may encounter rendering issues if the NVIDIA GPU is not explicitly selected. You may remove these variables from the command if they do not apply to your system. However, if you experience black or missing textures, setting these environment variables inside the container may resolve the issue.

```Bash
cd ${VIRTR}
docker build -t virtr \
  --build-arg USERID=$(id -u) \
  --build-arg GROUPID=$(id -g) \
  --build-arg USERNAME=$(whoami) \
  --build-arg HOMEDIR=${HOME} .

docker run -it --name virtr \
  --privileged \
  --network=host \
  --ipc=host \
  --gpus=all \
  -e DISPLAY=$DISPLAY \
  -e __NV_PRIME_RENDER_OFFLOAD=1 \
  -e __GLX_VENDOR_LIBRARY_NAME=nvidia \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v ${VTRROOT}:${VTRROOT}:rw \
  -v ${HOME}/.ignition:${HOME}/.ignition:rw \
  -v ${HOME}/.gz:${HOME}/.gz:rw \
  -v /dev:/dev \
  virtr
```


## Building VirT&R
Inside the Docker container:
```Bash
# Source ROS2 and vtr3 packages
source /opt/ros/humble/setup.bash
source ${VTRSRC}/main/install/setup.bash

# Build and install VirT&R packages
cd ${VIRTRWS}
colcon build --symlink-install

# You may use the following alias to source ROS2, vtr3, and virtr
source_virtr
```

## Robot Setup
This version of VirT&R uses code from Clearpath Robotics to launch robots and sensors in Gazebo Ignition with bridges to ROS 2 ([clearpath_simulator](https://github.com/utiasASRL/clearpath_simulator/tree/fc29a30b6f93ee4b8652bbbe64b13e9365fde1bb)).

To use a Clearpath robot, modify `${VIRTR}/clearpath/robot.yaml`, or equivilantly `${CLEARPATHCONFIG}/robot.yaml`, to match the desired robot and sensor configuration. Once configured, run the following executable to generate platform-specific launch files. More documentation on how to set up the `robot.yaml` file is available in the ([Clearpath documentation](https://docs.clearpathrobotics.com/docs/ros2humble/ros/config/yaml/overview)).
```Bash
ros2 run clearpath_generator_common generate_bash -s ${CLEARPATHCONFIG}
```

If you are using a custom robot, create a dedicated folder, such as `${VIRTR}/custom_robots/my_robot/`, containing the required configuration, launch, and robot description files. See the `hunter2` platform for reference. These files are primarily used to configure the required Gazebo-ROS2 bridges and allow the Clearpath simulator code to launch the robot into Gazebo as if it were a standard Clearpath robot.

Any custom robot meshes or materials referenced by the `.urdf.xacro` or `.xacro` files must be included under `${VIRTR}/data/robots/my_robot/` and correctly referenced in the robot description files.

The `IGN_GAZEBO_RESOURCE_PATH` and `GZ_SIM_RESOURCE_PATH` environment variables are set to `${VIRTR}/data` in the Dockerfile. This allows `.STL` files to be referenced directly in robot description files, for example:

`filename="model://robots/my_robot/meshes/base_link.STL"`

Future work includes removing the dependency on the Clearpath libraries and replacing it with dedicated simulation code that is more generalizable.

## Map Setup
Ensure relevent files (`mesh.obj, mesh.mtl, texture.jpg, pointcloud.pcd`) exist under `${VIRTR}/data/map_name/`. To build an `.sdf` file that references this model in Gazebo, run:
```Bash
cd ${VIRTR}
python3 launch/create_gazebo_sdf.py data/map_name
```

This creates the file `model.sdf` in the same directory. The generated file references the custom mesh and sets up the required simulation parameters.

You may want to modify the friction settings in this file if the robot model interacts poorly or unrealistically with the mesh. These settings are left to the user’s discretion, since robot models and description files may define collision geometry and physics properties differently.

## Example Usage

### Launching the Simulator

To run the simulator with a custom map and the Clearpath robot defined in `${CLEARPATHCONFIG}`, run:

```bash
ros2 launch clearpath_gz simulation.launch.py setup_path:="${CLEARPATHCONFIG}/" world:=${GZ_SIM_RESOURCE_PATH}/map_name/model generate:=false
```

The `generate:=false` argument prevents custom launch files from being generated. This argument is set to `true` by default and should be set to `true` at least once when using a Clearpath robot.

If you are using a custom robot, you must also specify the path to the custom launch files:

```bash
ros2 launch clearpath_gz simulation.launch.py setup_path:="${VIRTR}/custom_robots/hunter2/" generate:=false robot:="hunter2" world:=${GZ_SIM_RESOURCE_PATH}/map_name/model
```

These commands should start the simulation with the robot loaded into the specified map. If a gamepad or controller is connected to your computer, teleoperating the robot should be straightforward. Controller behavior can also be configured in the launch configuration YAML files located in the same directory and subdirectories of the robot description files.

### Creating a Virtual Teach Path

While the simulator is running, position the robot at the desired starting point. Then run the command below and begin teleoperating the robot along the desired path. Press `Ctrl-C` when you are finished teaching.

```bash
ros2 run relative_transform_recorder save_path --ros-args -p map:=map_name
```

This creates the following file:

```text
${VIRTR}/data/map_name/paths/relative_transforms.csv
```

### Creating a VTR3 Pose Graph

After saving the relative transforms from the virtual teach, create the pose graph and point cloud submaps used by VTR3 with the following command:

```bash
ros2 run vtr_virtual_teach generate_global_map map_name 0
```

The `0` argument specifies that lidar point cloud submaps should be generated rather than radar point cloud submaps. The radar pipeline has not been tested in this version of VirT&R, although the submap generation code has not been substantially modified from the original version.


## Download vtr3_posegraph_tools
It is also recommended to download the following project as well (https://github.com/utiasASRL/vtr3_pose_graph), as it contains useful scripts for ensuring the teach maps are made correctly. Scripts in this project are referenced in the 'Using VirT&R' documentation. Download it to your local filesystem in the same directory (${VTRROOT}) alongside this code if you do not already have it. The `virtual_teach_edits` branch should have relevent scripts specific to VirT&R for visualization.

```Bash
cd ${VTRROOT}
git clone virtual_teach_edits git@github.com:utiasASRL/vtr3_pose_graph.git
```

## Create a python venv to install the posegraph python tools
Within the running VTR3 Docker container, create a virtual environment at `${VTRROOT}`. (If you already have these tools installed, skip this step.)

```Bash
cd ${VTRROOT}
virtualenv venv
source venv/bin/activate  
cd vtr3_posegraph_tools
pip3 install -e .
```

# Additional VirT&R Documention

The following instructions are from the README.md from the previous/original VirT&R branch.

## Please consult the 'Using VirT&R' documentation for detailed steps on how to proceed. 
https://docs.google.com/document/d/1vdrQSJKqGCwA7cPzZpHC-xvCbrQ00U4pSuBSXlRZtOs/edit?usp=sharing

## Example Dataset
An example dataset can be downloaded from this Google Drive link. It contains all elements created as a result of the steps in this pipeline (not just the input and output data), so you can follow along and ensure a good result from your installation of the pipeline.

The structure of the data in the example dataset folder 'test_press' should be replicated for all data used with this pipeline for the helper scripts to function correctly (although by running the first launch script, the correct structure is created for subsequent scripts and so on, so it should be handled for you, provided you initially set up the .csv and .mp4 correctly - file paths are left configurable so that you have more control over your file management.)

DATASET DOWNLOAD:
https://drive.google.com/drive/folders/1TpRJCtvYFxTDJrL1TxS9-hO1WO6BE5z0?usp=sharing

## Helper scripts used to run the programs
The following helper scripts have been created to automate some tedious or menial aspects involved in creating a virtual teach map. Below, they are specific to the test_press dataset and can be run sequentially according to the documentation. The helper scripts, and when to use them, are referenced in the 'Using VirT&R' documentation. To use the example dataset test_press, put the folder you downloaded from the link into the /data folder in the vtr_virtual_teach_wrapper. The video can't be compressed, so it's often downloaded separately. Just make sure it's called DJI_0001-001.MP4 as it is in the test_press folder too. These commands should be run outside the docker container.

```Bash
chmod +x ImageExtraction.sh ImageProcessor.sh Gazebo.sh TeachMap.sh        

./ImageExtraction.sh "${VTRROOT}/virtual_teach_vtr_wrapper/data/test_press/DJIFlightRecord_2025-02-22_[11-59-34].csv" "${VTRROOT}/virtual_teach_vtr_wrapper/data/test_press/DJI_0001-001.MP4" "1740243662000" "${VTRROOT}/virtual_teach_vtr_wrapper/data/test_press/images" "${VTRROOT}/virtual_teach_vtr_wrapper/data/test_press/all_image_poses.txt" DJI

# makes: images folder and all_image_poses.txt file


./ImageProcessor.sh "${VTRROOT}/virtual_teach_vtr_wrapper/data/test_press/images" "${VTRROOT}/virtual_teach_vtr_wrapper/data/test_press/colmap"  "${VTRROOT}/virtual_teach_vtr_wrapper/data/test_press/all_image_poses.txt" "${VTRROOT}/virtual_teach_vtr_wrapper/data/test_press/colmap/filtered.txt" "0.01" "${VTRROOT}/virtual_teach_vtr_wrapper/data/test_press/colmap/database.db" "${VTRROOT}/virtual_teach_vtr_wrapper/data/test_press/colmap/Scaled" "press_test"

# makes: output folder of filtered images corresponding to filtered_and_scaled.txt (also created from this), database.db, the colmap folder, and the scaled project folder (which will hold the 3 generated .bin files produced)


./Gazebo.sh "${VTRROOT}/virtual_teach_vtr_wrapper/data/test_press/meshes/mesh.dae" "${VTRROOT}/virtual_teach_vtr_wrapper/data/test_press/meshes/material_0.png" "test_press_world"

# makes: .world, .launch, .config, and .sdf files specific to the dataset


./TeachMap.sh "${VTRROOT}/virtual_teach_vtr_wrapper/data/test_press/pointclouds/point_cloud.ply" "${VTRROOT}/virtual_teach_vtr_wrapper/data/test_press/paths/relative_transforms.csv" "test_press"

# makes: virtual teach map (graph folder used to run with Lidar Teach and Repeat)

```


## [License](./LICENSE)
