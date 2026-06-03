FROM vtr3

ARG GROUPID=0
ARG USERID=0
ARG USERNAME=root
ARG HOMEDIR=/root

# Test consistency with vtr3 image
RUN test -d "${HOMEDIR}" && \
    id "${USERNAME}" && \
    test "$(id -u ${USERNAME})" = "${USERID}" && \
    test "$(id -g ${USERNAME})" = "${GROUPID}"

# Set non-interactive mode.
ENV DEBIAN_FRONTEND=noninteractive

# Test consistency with vtr3 image
RUN test "$VTRROOT" = "${HOMEDIR}/ASRL/vtr3"
RUN test "$VTRSRC" = "$VTRROOT/src" && \
    test "$VTRDATA" = "$VTRROOT/data" && \
    test "$VTRTEMP" = "$VTRROOT/temp" && \
    test "$VTRMODELS" = "$VTRROOT/models" && \
    test "$GRIZZLY" = "$VTRROOT/grizzly" && \
    test "$WARTHOG" = "$VTRROOT/warthog"

ENV VIRTR=${VTRROOT}/virtr
ENV VIRTRWS=${VIRTR}/ros2
ENV CLEARPATHCONFIG=${VIRTR}/clearpath

# Setting Gazebo resource paths to use local data/
ENV IGN_GAZEBO_RESOURCE_PATH=${VIRTR}/data
ENV GZ_SIM_RESOURCE_PATH=${VIRTR}/data

RUN echo "alias source_virtr='source /opt/ros/humble/setup.bash; source ${VTRSRC}/main/install/setup.bash; source ${VIRTRWS}/install/setup.bash'" >> ${HOMEDIR}/.bashrc
RUN echo "alias build_virtr='source /opt/ros/humble/setup.bash && cd ${VTRSRC}/main && colcon build --symlink-install && source ${VTRSRC}/main/install/setup.bash && cd ${VIRTRWS} && colcon build --symlink-install'" >> ${HOMEDIR}/.bashrc

# Switch to root to install dependencies
USER 0:0

# vtr3 should have these, but double check and install if missing.
RUN apt-get update && apt-get install -q -y --no-install-recommends --no-upgrade \
    curl \
    lsb-release \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Add OSRF Gazebo package repository.
RUN curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
        > /etc/apt/sources.list.d/gazebo-stable.list

# Install Gazebo Fortress.
RUN apt-get update && apt-get install -q -y --no-install-recommends --no-upgrade \
    ignition-fortress \
    && rm -rf /var/lib/apt/lists/*

# Add Clearpath package repository and rosdep rules.
RUN curl -fsSL https://packages.clearpathrobotics.com/public.key \
      | gpg --dearmor -o /usr/share/keyrings/clearpath-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/clearpath-archive-keyring.gpg] https://packages.clearpathrobotics.com/stable/ubuntu $(lsb_release -cs) main" \
      > /etc/apt/sources.list.d/clearpath-latest.list

# Install Clearpath simulation dependencies.
RUN apt-get update && apt-get install -q -y --no-install-recommends --no-upgrade \
    ros-humble-clearpath-common \
    ros-humble-clearpath-msgs \
    ros-humble-clearpath-config \
    ros-humble-clearpath-viz \
    && rm -rf /var/lib/apt/lists/*
# ros-humble-clearpath-desktop

# Install Gazebo Fortress ROS2 dependencies (These could maybe be removed).
RUN apt-get update && apt-get install -q -y --no-install-recommends --no-upgrade \
    ros-humble-ros-gz \
    ros-humble-ign-ros2-control \
    && rm -rf /var/lib/apt/lists/*
# ros-humble-ros-gz-bridge
# python3-gz-transport13 \
# python3-gz-msgs10 \

# Install other ROS2 dependencies
RUN apt-get update && apt-get install -q -y --no-install-recommends --no-upgrade \
    ros-humble-teleop-twist-keyboard \
    ros-humble-teleop-twist-joy \
    && rm -rf /var/lib/apt/lists/*
   
# Original VirTR packages
# RUN pip install --upgrade pip setuptools
# RUN pip install "jupyter_client>=5.3.4,<8"
# RUN pip install --upgrade numpy
# RUN pip install --ignore-installed scipy pandas matplotlib opencv-python testresources open3d asrl-pylgmath pycollada plotly opencv-python
# RUN pip install --ignore-installed --upgrade numpy pip pyOpenSSL cryptography

# Python packages specific to VirTR.
# Preinstall some packages to avoid open3d overwriting numpy version
RUN apt update && apt install -q -y --no-install-recommends --no-upgrade \
    python3-jupyter-client \
    python3-numpy \
    python3-scipy \
    python3-sklearn \
    python3-pandas \
    python3-matplotlib \
    python3-opencv \
    python3-testresources \
    python3-collada \
    python3-openssl \
    python3-cryptography \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir open3d asrl-pylgmath 

# RUN python3 -m pip install --no-cache-dir \
#     "jupyter_client>=5.3.4,<8" \
#     numpy \
#     scipy \
#     pandas \
#     matplotlib \
#     opencv-python \
#     testresources \
#     open3d \
#     asrl-pylgmath \
#     pycollada \
#     plotly \
#     pyOpenSSL \
#     cryptography

# Blender could actually be removed - you can run Gazebo with .obj/.mtl files directly instead of .dae
RUN python3 -m pip install --no-cache-dir \
    --extra-index-url https://download.blender.org/pypi/ \
    "bpy==4.0.0"
    
USER ${USERID}:${GROUPID}

WORKDIR ${VIRTRWS}

# Might require this
# RUN chmod +x ${VIRTRWS}/src/warthog_gazebo_path_publisher/warthog_gazebo_path_publisher/save_path.py

CMD ["/bin/bash", "-l"]
