import os
import sys
import pandas as pd
import matplotlib.pyplot as plt


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <map_name>")
        return -1

    map_name = sys.argv[1]

    print(f"Map name: {map_name}")

    # Get environment variable for VIRTR root directory
    virtr_root = os.getenv("VIRTR")
    csv_file = os.path.join(virtr_root, "data", map_name, "paths", "robot_path.csv")

    # Load the CSV file
    try:
        data = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"Error: File {csv_file} not found.")
        exit(-1)

    # Check if the CSV contains the necessary columns
    if not {"x", "y", "z"}.issubset(data.columns):
        print("Error: CSV file does not contain 'x', 'y', 'z' columns.")
        exit(-1)

    x = data['x']
    y = data['y']
    z = data['z']

    max_range = max(
        x.max() - x.min(),
        y.max() - y.min(),
        z.max() - z.min()
    )

    x_mid = 0.5 * (x.max() + x.min())
    y_mid = 0.5 * (y.max() + y.min())
    z_mid = 0.5 * (z.max() + z.min())

    half_range = 0.5 * max_range

    # Plot the 3D path
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    ax.plot(x, y, z, label='Robot Path', marker='o', linestyle='None')
    # ax.plot(x, y, z, label='Robot Path', marker='o')
    ax.set_xlabel('X (meters)')
    ax.set_ylabel('Y (meters)')
    ax.set_zlabel('Z (meters)')
    ax.set_xlim(x_mid - half_range, x_mid + half_range)
    ax.set_ylim(y_mid - half_range, y_mid + half_range)
    ax.set_zlim(z_mid - half_range, z_mid + half_range)
    ax.set_title('Robot Path Visualization')
    ax.legend()

    # Show the plot
    plt.show()


if __name__ == "__main__":
    main()