/**
 * Docker Compose deployment types
 */

export interface ComposeServicePort {
  host_port: number;
  container_port: number;
  protocol: 'tcp' | 'udp';
  host_ip: string;
}

export interface ComposeServiceVolume {
  host_path: string;
  container_path: string;
  mode: 'rw' | 'ro';
  type: 'bind' | 'volume' | 'tmpfs';
}

export interface ComposeServiceNetwork {
  name: string;
  aliases?: string[];
  ipv4_address?: string;
}

export interface ComposeModificationRequest {
  // Source and target information
  compose_content: string;
  target_device: string;
  
  // Service configuration
  service_name?: string;
  
  // Path modifications
  update_appdata_paths: boolean;
  custom_appdata_path?: string;
  
  // Port management
  auto_assign_ports: boolean;
  port_range_start: number;
  port_range_end: number;
  custom_port_mappings?: Record<string, number>;
  
  // Network configuration
  update_networks: boolean;
  default_network?: string;
  
  // Proxy configuration
  generate_proxy_configs: boolean;
  base_domain?: string;
  
  // Deployment settings
  deployment_path?: string;
  create_directories: boolean;
}

export interface ComposeModificationResult {
  // Operation metadata
  device: string;
  service_name?: string;
  timestamp: string;
  success: boolean;
  execution_time_ms: number;
  
  // Modified compose content
  modified_compose: string;
  original_compose_hash: string;
  modified_compose_hash: string;
  
  // Changes applied
  changes_applied: string[];
  
  // Port assignments
  port_assignments: Record<string, ComposeServicePort[]>;
  
  // Volume path updates
  volume_updates: Record<string, ComposeServiceVolume[]>;
  
  // Network configurations
  network_configs: Record<string, ComposeServiceNetwork>;
  
  // Proxy configurations generated
  proxy_configs: Array<Record<string, any>>;
  
  // Deployment information
  deployment_path?: string;
  directories_created: string[];
  
  // Warnings and errors
  warnings: string[];
  errors: string[];
  
  // Device information
  device_info: Record<string, any>;
}

export interface ComposeDeploymentRequest {
  device: string;
  compose_content: string;
  deployment_path: string;
  
  // Deployment options
  start_services: boolean;
  pull_images: boolean;
  recreate_containers: boolean;
  
  // Directory management
  create_directories: boolean;
  backup_existing: boolean;
  
  // Service management
  services_to_start?: string[];
  services_to_stop?: string[];
}

export interface ComposeDeploymentResult {
  device: string;
  deployment_path: string;
  timestamp: string;
  success: boolean;
  execution_time_ms: number;
  
  // Files managed
  compose_file_created: boolean;
  backup_file_path?: string;
  directories_created: string[];
  
  // Docker operations
  images_pulled: string[];
  containers_created: string[];
  containers_started: string[];
  containers_stopped: string[];
  
  // Service status
  service_status: Record<string, string>;
  
  // Execution logs
  logs: string[];
  warnings: string[];
  errors: string[];
}

export interface ComposeModifyAndDeployRequest {
  // Combines modification and deployment
  compose_content: string;
  target_device: string;
  
  // Modification settings
  service_name?: string;
  update_appdata_paths: boolean;
  custom_appdata_path?: string;
  auto_assign_ports: boolean;
  port_range_start: number;
  port_range_end: number;
  generate_proxy_configs: boolean;
  base_domain?: string;
  
  // Deployment settings
  deployment_path?: string;
  start_services: boolean;
  pull_images: boolean;
}

export interface ComposeModifyAndDeployResult {
  modification_result: ComposeModificationResult;
  deployment_result: ComposeDeploymentResult;
  overall_success: boolean;
  total_execution_time_ms: number;
}

// Port scanning for compose deployment
export interface ComposePortScanRequest {
  device: string;
  port_range_start: number;
  port_range_end: number;
  protocol: 'tcp' | 'udp';
  timeout: number;
}

export interface ComposePortScanResult {
  device: string;
  available_ports: number[];
  used_ports: Array<{
    port: number;
    process?: string;
    service?: string;
  }>;
  scan_timestamp: string;
  scan_duration_ms: number;
}

// Docker network scanning
export interface DockerNetworkScanRequest {
  device: string;
  include_system_networks: boolean;
}

export interface DockerNetworkScanResult {
  device: string;
  networks: Array<{
    name: string;
    driver: string;
    subnet?: string;
    gateway?: string;
    is_system: boolean;
    container_count: number;
  }>;
  recommended_network?: string;
  scan_timestamp: string;
}