from pathlib import Path
import argparse
import os
import sys

REQUIRED_FILES = [
    "mesh.obj",
    "mesh.mtl",
    "texture.jpg",
]

def validate_map_folder(map_dir: Path) -> None:
    if not map_dir.exists():
        raise FileNotFoundError(f"Folder does not exist: {map_dir}")

    if not map_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {map_dir}")

    missing = []

    for filename in REQUIRED_FILES:
        if not (map_dir / filename).is_file():
            missing.append(filename)

    if missing:
        raise FileNotFoundError(
            "Missing required file(s): "
            + ", ".join(missing)
            + f"\nExpected these files inside: {map_dir}"
        )


def make_model_config(map_name: str) -> str:
    return f"""<?xml version="1.0"?>
<model>
  <name>{map_name}</name>
  <version>1.0</version>
  <sdf version="1.8">model.sdf</sdf>

  <author>
    <name>{map_name}</name>
    <email></email>
  </author>

  <description>
    Generated Gazebo model for {map_name}.
  </description>
</model>
"""


def make_model_sdf(map_name: str) -> str:
    return f"""<?xml version='1.0' encoding='ASCII'?>
<sdf version="1.8">
  <world name='{map_name}'>
    <physics type="ode">
      <max_step_size>0.025</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>

    <plugin name='ignition::gazebo::systems::Physics' filename='libignition-gazebo-physics-system.so'/>
    <plugin name='ignition::gazebo::systems::UserCommands' filename='libignition-gazebo-user-commands-system.so'/>
    <plugin name='ignition::gazebo::systems::SceneBroadcaster' filename='libignition-gazebo-scene-broadcaster-system.so'/>

    <plugin name="ignition::gazebo::systems::Sensors" filename="libignition-gazebo-sensors-system.so">
      <render_engine>ogre2</render_engine>
    </plugin>

    <plugin name="ignition::gazebo::systems::Imu" filename="libignition-gazebo-imu-system.so"/>
    <plugin name="ignition::gazebo::systems::NavSat" filename="libignition-gazebo-navsat-system.so"/>

    <scene>
      <ambient>1 1 1 1</ambient>
      <background>0.3 0.7 0.9 1</background>
      <shadows>0</shadows>
      <grid>false</grid>
    </scene>

    <light type="directional" name="sun">
      <cast_shadows>false</cast_shadows>
      <pose>0 0 100 0 0 0</pose>
      <diffuse>1 1 1 1</diffuse>
      <specular>0.5 0.5 0.5 1</specular>
      <direction>-0.5 0.1 -0.9</direction>
    </light>

    <spherical_coordinates>
      <surface_model>EARTH_WGS84</surface_model>
      <world_frame_orientation>ENU</world_frame_orientation>
      <latitude_deg>-22.986687</latitude_deg>
      <longitude_deg>-43.202501</longitude_deg>
      <elevation>0</elevation>
      <heading_deg>0</heading_deg>
    </spherical_coordinates>

    <model name="{map_name}_model">
      <static>true</static>

      <link name="link">
        <visual name="visual">
          <geometry>
            <mesh>
              <uri>model://{map_name}/mesh.obj</uri>
              <scale>1 1 1</scale>
            </mesh>
          </geometry>
        </visual>

        <collision name="collision">
          <geometry>
            <mesh>
              <uri>model://{map_name}/mesh.obj</uri>
              <scale>1 1 1</scale>
            </mesh>
          </geometry>

          <surface>
            <friction>
              <ode>
                <mu>10.0</mu>
                <mu2>10.0</mu2>
                <slip1>0.0</slip1>
                <slip2>0.0</slip2>
              </ode>
            </friction>

            <contact>
              <ode>
                <min_depth>0.3</min_depth>
              </ode>
            </contact>
          </surface>
        </collision>
      </link>
    </model>
  </world>
</sdf>
"""


def create_files(map_dir: Path, overwrite: bool = False) -> None:
    map_dir = map_dir.resolve()
    map_name = map_dir.name

    validate_map_folder(map_dir)

    sdf_path = map_dir / "model.sdf"
    config_path = map_dir / "model.config"

    if not overwrite:
        existing = [
            str(path.name)
            for path in [sdf_path, config_path]
            if path.exists()
        ]

        if existing:
            raise FileExistsError(
                "Output file(s) already exist: "
                + ", ".join(existing)
                + "\nUse --overwrite to replace them."
            )

    sdf_path.write_text(make_model_sdf(map_name), encoding="utf-8")
    config_path.write_text(make_model_config(map_name), encoding="utf-8")

    print(f"Created: {sdf_path}")
    print(f"Created: {config_path}")
    print(f"Model name: {map_name}")
    print("Checked required files:")
    for filename in REQUIRED_FILES:
        print(f"  - {filename}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create model.sdf and model.config for a Gazebo map folder."
    )

    parser.add_argument(
        "map_folder",
        help="Folder containing mesh.obj, mesh.mtl, and texture.jpg",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing model.sdf and model.config",
    )

    args = parser.parse_args()

    virtr = os.environ.get("VIRTR")
    if not virtr: raise EnvironmentError("VIRTR environment variable is not set. Expected map folders under ${VIRTR}/data/")
    data_dir = Path(virtr).expanduser().resolve() / "data"

    map_dir = data_dir / args.map_folder
    
    try:
        create_files(map_dir, overwrite=args.overwrite)
        return 0
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())