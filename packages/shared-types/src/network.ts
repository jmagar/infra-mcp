/**
 * Network-related types
 */

import { PaginatedResponse } from './common';

export type InterfaceType = 
  | 'ethernet'
  | 'wifi'
  | 'loopback'
  | 'bridge'
  | 'vlan'
  | 'bond'
  | 'tun'
  | 'tap'
  | 'ppp'
  | 'can'
  | 'infiniband';

export type InterfaceState = 'up' | 'down' | 'unknown';
export type DuplexMode = 'full' | 'half' | 'unknown';

export interface NetworkInterfaceBase {
  interface_name: string;
  interface_type: InterfaceType;
  mac_address?: string;
  ip_addresses: string[];
  mtu?: number;
  speed_mbps?: number;
  duplex?: DuplexMode;
  state: InterfaceState;
  rx_bytes?: number;
  tx_bytes?: number;
  rx_packets?: number;
  tx_packets?: number;
  rx_errors?: number;
  tx_errors?: number;
  rx_dropped?: number;
  tx_dropped?: number;
}

export interface NetworkInterfaceCreate extends NetworkInterfaceBase {
  device_id: string;
}

export interface NetworkInterfaceResponse extends NetworkInterfaceBase {
  time: string;
  device_id: string;
  utilization_percent?: number;
  error_rate?: number;
}

export type NetworkInterfaceList = PaginatedResponse<NetworkInterfaceResponse>;

// Docker network types
export type DockerNetworkDriver = 'bridge' | 'host' | 'none' | 'overlay' | 'macvlan' | 'ipvlan';
export type DockerNetworkScope = 'local' | 'global' | 'swarm';

export interface DockerNetworkBase {
  network_id: string;
  network_name: string;
  driver: DockerNetworkDriver;
  scope: DockerNetworkScope;
  subnet?: string;
  gateway?: string;
  containers_count: number;
  labels: Record<string, string>;
  options: Record<string, any>;
  config: Record<string, any>;
}

export interface DockerNetworkCreate extends DockerNetworkBase {
  device_id: string;
}

export interface DockerNetworkResponse extends DockerNetworkBase {
  device_id: string;
  created_at: string;
  updated_at?: string;
}

export type DockerNetworkList = PaginatedResponse<DockerNetworkResponse>;

// Network statistics
export interface NetworkStatistics {
  device_id: string;
  interface_name: string;
  period_start: string;
  period_end: string;
  
  // Traffic statistics
  total_rx_bytes: number;
  total_tx_bytes: number;
  avg_rx_rate_mbps: number;
  avg_tx_rate_mbps: number;
  peak_rx_rate_mbps: number;
  peak_tx_rate_mbps: number;
  
  // Error statistics
  total_errors: number;
  error_rate: number;
  packet_loss_percent: number;
  
  // Utilization
  avg_utilization_percent: number;
  peak_utilization_percent: number;
}

// Port scanning
export interface PortScanResult {
  device_id: string;
  hostname: string;
  scan_timestamp: string;
  open_ports: Array<{
    port: number;
    protocol: 'tcp' | 'udp';
    service?: string;
    version?: string;
    state: 'open' | 'closed' | 'filtered';
  }>;
  total_scanned: number;
  scan_duration_ms: number;
}

// Network connectivity
export interface NetworkConnectivity {
  device_id: string;
  hostname: string;
  
  // Connectivity tests
  internet_access: boolean;
  dns_resolution: boolean;
  gateway_reachable: boolean;
  
  // Latency measurements
  gateway_latency_ms?: number;
  dns_latency_ms?: number;
  internet_latency_ms?: number;
  
  // Route information
  default_gateway?: string;
  dns_servers: string[];
  routes: Array<{
    destination: string;
    gateway: string;
    interface: string;
    metric: number;
  }>;
  
  test_timestamp: string;
}

// Bandwidth monitoring
export interface BandwidthUsage {
  device_id: string;
  interface_name: string;
  timestamp: string;
  
  // Current rates
  rx_rate_mbps: number;
  tx_rate_mbps: number;
  
  // Cumulative totals
  rx_total_gb: number;
  tx_total_gb: number;
  
  // Connection tracking
  active_connections: number;
  new_connections_per_sec: number;
  
  // Protocol breakdown
  protocol_stats: Record<string, {
    rx_bytes: number;
    tx_bytes: number;
    connections: number;
  }>;
}

// Network topology
export interface NetworkTopology {
  nodes: Array<{
    id: string;
    type: 'device' | 'switch' | 'router' | 'container';
    name: string;
    ip_addresses: string[];
    status: 'online' | 'offline';
  }>;
  edges: Array<{
    source: string;
    target: string;
    type: 'physical' | 'virtual' | 'container';
    bandwidth_mbps?: number;
    latency_ms?: number;
  }>;
  networks: Array<{
    id: string;
    name: string;
    subnet: string;
    type: 'physical' | 'docker' | 'virtual';
    members: string[];
  }>;
  generated_at: string;
}