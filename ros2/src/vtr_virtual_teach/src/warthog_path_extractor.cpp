#include <vtr_logging/logging_init.hpp>  
#include <iostream>
#include <fstream>
#include <memory>
#include <vtr_pose_graph/serializable/rc_graph.hpp>

std::string requireEnvVar(const std::string& name) {
  const char* value = std::getenv(name.c_str());

  if (value == nullptr || std::string(value).empty()) {
    throw std::runtime_error("Required environment variable is not set: " + name);
  }

  return std::string(value);
}

int main(int argc, char** argv) {

  if (argc != 2 && argc != 3) {
    std::cerr << "Usage:\n"
              << "  " << argv[0] << " <map_name>\n"
              << "  OR\n"
              << "  " << argv[0] << " <graph_folder> <output_csv_path>\n";
    return -1;
  }

  std::string graph_folder;
  std::string output_csv_path;

  if (argc == 3) {
    graph_folder = argv[1];
    output_csv_path = argv[2];
  } else {
    const std::string map_name = argv[1];

    const std::string virtr_root = requireEnvVar("VIRTR");
    const std::string data_folder = virtr_root + "/data/" + map_name;

    graph_folder = data_folder + "/graph";
    output_csv_path = data_folder + "/paths/robot_path.csv";

    if (!std::filesystem::exists(graph_folder)) {
      throw std::runtime_error(
          "Missing expected graph folder: " + graph_folder +
          "\nPlease rename/move your graph folder to graph, or use explicit-path mode.");
    }

    std::filesystem::create_directories(data_folder + "/paths");
  }

  LOG(INFO) << "Graph folder: " << graph_folder;
  LOG(INFO) << "Output CSV path: " << output_csv_path;

  vtr::logging::configureLogging();  // Initialize logging

  // Load the pose graph
  using Graph = vtr::pose_graph::RCGraph;
  std::shared_ptr<Graph> graph;
  try {
    graph = std::make_shared<Graph>(graph_folder); 
    LOG(INFO) << "Graph loaded successfully from: " << graph_folder;
  } catch (const std::exception& e) {
    LOG(ERROR) << "Error loading graph: " << e.what();
    return -1;
  }
  // Open a CSV file to save the path
  std::ofstream csv_file(output_csv_path);
  if (!csv_file.is_open()) {
    LOG(ERROR) << "Error: Could not open output file!";
    return -1;
  }
  LOG(INFO) << "Opened " << output_csv_path << " for writing.";
  // Write the CSV header
  csv_file << "x,y,z\n";
  // Iterate through the vertices in the graph
  for (const auto& vertex : *graph) {
    auto pose_with_cov = vertex.T();
    const lgmath::se3::Transformation& pose = pose_with_cov;
    // Extract translation from the transformation matrix
    auto matrix = pose.matrix();
    if (matrix.isIdentity()) {
        LOG(WARNING) << "Identity matrix encountered, skipping vertex.";
        continue;
    }
    auto translation = matrix.block<3, 1>(0, 3);
    // Write the translation to the CSV file
    csv_file << translation(0) << "," << translation(1) << "," << translation(2) << "\n";
  }
  // Close the CSV file
  csv_file.close();
  LOG(INFO) << "Robot path saved to robot_path.csv";
  return 0;
}






