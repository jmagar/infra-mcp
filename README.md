# Infrastructor 🏗️

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/Framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![MCP](https://img.shields.io/badge/MCP-FastMCP-orange.svg)](https://pypi.org/project/fastmcp/)

**A comprehensive, API-driven infrastructure management and monitoring platform.**

`infrastructor` provides a powerful and flexible solution for managing and monitoring your entire infrastructure, from bare-metal servers to Docker containers. It combines a robust FastAPI backend with a flexible `fastmcp` server, giving you the power to manage your infrastructure through a REST API or a command-line interface.

## ✨ Features

*   **Comprehensive Monitoring:** Keep a close eye on all aspects of your infrastructure, including system metrics, drive health, container performance, and ZFS filesystem management.
*   **Container Management:** Complete Docker container lifecycle management including start, stop, restart, remove, stats monitoring, and command execution inside containers.
*   **Docker Compose Deployment:** Automatically modify and deploy docker-compose files to target devices with path updates, port assignment, network configuration, and SWAG proxy setup.
*   **Device Management:** Register and manage all of your infrastructure devices in a central location.
*   **ZFS Management:** Complete ZFS filesystem management including pools, datasets, snapshots, health monitoring, optimization recommendations, and comprehensive MCP tools for all ZFS operations.
*   **Proxy Configuration Management:** Seamlessly manage your SWAG reverse proxy configurations.
*   **Time-Series Database:** `infrastructor` uses TimescaleDB to store and analyze time-series data, providing powerful insights into your infrastructure's performance over time.
*   **Dual-Interface:** Interact with your infrastructure through a powerful REST API or a flexible `fastmcp` command-line interface.

## 🏛️ Architecture

`infrastructor` uses a dual-server architecture:

*   **FastAPI REST API:** A robust backend that provides a RESTful interface for managing and monitoring your infrastructure.
*   **`fastmcp` Server:** A flexible command-line interface that acts as a client to the REST API, providing a powerful and scriptable way to interact with your infrastructure.

This architecture ensures that all operations, whether initiated from the API or the MCP, go through the same centralized logic, providing a consistent and reliable management experience.

```text
+-----------------+      +-----------------+      +-----------------+
|                 |      |                 |      |                 |
|   FastAPI REST  |<---->|   `fastmcp`     |<---->|   User          |
|   API Server    |      |   Server        |      |                 |
|                 |      |                 |      |                 |
+-----------------+      +-----------------+      +-----------------+
        ^                      ^
        |                      |
        v                      v
+-----------------------------------------------------------------+
|                                                                 |
|   TimescaleDB (PostgreSQL)                                      |
|                                                                 |
+-----------------------------------------------------------------+
```

## 🚀 Getting Started

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/jmagar/infrastructor.git
    cd infrastructor
    ```

2.  **Set up the environment:**
    *   Copy `.env.example` to `.env` and fill in the required values.
    *   **Security Note:** The `.env` file contains sensitive database credentials. Make sure to:
        - Change the default password (`change_me_in_production`) to a secure password
        - Never commit the `.env` file to version control
        - The `DATABASE_URI` variable is automatically used by MCP servers for secure database connections
3.  **Start the database:**

    ```bash
    docker-compose up -d
    ```

4.  **Install the dependencies:**

    ```bash
    pip install -e .[dev]
    ```

5.  **Run the database migrations:**

    ```bash
    cd apps/backend && alembic upgrade head
    ```

6.  **Start the servers:**

    ```bash
    ./dev.sh start
    ```


## Usage

The `dev.sh` script is the primary way to manage the development environment.

*   **Start the servers:**

    ```bash
    ./dev.sh start
    ```

*   **Stop the servers:**

    ```bash
    ./dev.sh stop
    ```

*   **Restart the servers:**

    ```bash
    ./dev.sh restart
    ```

*   **View the logs:**

    ```bash
    ./dev.sh logs
    ```

## 📖 API Endpoints

The REST API provides a comprehensive set of endpoints for managing your infrastructure.

### Common

*   `GET /status`: Get the status of the API.
*   `GET /system-info`: Get information about the API server.
*   `GET /test-error`: Test the error handling system.

### Containers

*   `GET /containers/{hostname}`: List containers on a device.
*   `GET /containers/{hostname}/{container_name}`: Get information about a container.
*   `GET /containers/{hostname}/{container_name}/logs`: Get logs from a container.
*   `POST /containers/{hostname}/{container_name}/start`: Start a Docker container.
*   `POST /containers/{hostname}/{container_name}/stop`: Stop a Docker container.
*   `POST /containers/{hostname}/{container_name}/restart`: Restart a Docker container.
*   `DELETE /containers/{hostname}/{container_name}`: Remove a Docker container.
*   `GET /containers/{hostname}/{container_name}/stats`: Get real-time container statistics.
*   `POST /containers/{hostname}/{container_name}/exec`: Execute a command inside a container.

### Docker Compose Deployment

*   `POST /compose/modify`: Modify docker-compose content for deployment on target device.
*   `POST /compose/deploy`: Deploy docker-compose content to target device.
*   `POST /compose/modify-and-deploy`: Modify and deploy docker-compose in a single operation.
*   `GET /compose/download-modified/{device}`: Download modified docker-compose content as plain text.
*   `POST /compose/scan-ports`: Scan for available ports on target device.
*   `POST /compose/scan-networks`: Scan Docker networks on target device.
*   `GET /compose/proxy-configs/{device}/{service_name}`: Generate SWAG proxy configuration for a service.

### Devices

*   `POST /devices`: Create a new device.
*   `GET /devices`: List all devices.
*   `GET /devices/{hostname}`: Get a device by hostname.
*   `PUT /devices/{hostname}`: Update a device.
*   `DELETE /devices/{hostname}`: Delete a device.
*   `GET /devices/{hostname}/status`: Get the status of a device.
*   `GET /devices/{hostname}/summary`: Get a summary of a device.
*   `GET /devices/{hostname}/metrics`: Get metrics for a device.
*   `GET /devices/{hostname}/drives`: Get drive health for a device.
*   `GET /devices/{hostname}/drives/stats`: Get drive stats for a device.
*   `GET /devices/{hostname}/logs`: Get system logs for a device.

### Proxy

*   `GET /proxies/configs`: List all proxy configurations.
*   `GET /proxies/configs/{service_name}`: Get a proxy configuration.
*   `GET /proxies/configs/{service_name}/content`: Get the content of a proxy configuration.
*   `POST /proxies/scan`: Scan for new proxy configurations.
*   `POST /proxies/configs/{service_name}/sync`: Sync a proxy configuration.
*   `GET /proxies/summary`: Get a summary of the proxy configurations.
*   `GET /proxies/templates/{template_type}`: Get a proxy configuration template.
*   `GET /proxies/samples`: List all proxy configuration samples.
*   `GET /proxies/samples/{sample_name}`: Get a proxy configuration sample.

### ZFS Management

*   `GET /zfs/{hostname}/pools`: List all ZFS pools on a device.
*   `GET /zfs/{hostname}/pools/{pool_name}/status`: Get detailed status for a specific ZFS pool.
*   `GET /zfs/{hostname}/datasets`: List all ZFS datasets on a device.
*   `GET /zfs/{hostname}/datasets/{dataset_name}/properties`: Get properties for a specific ZFS dataset.
*   `GET /zfs/{hostname}/snapshots`: List all ZFS snapshots on a device.
*   `POST /zfs/{hostname}/snapshots`: Create a new ZFS snapshot.
*   `POST /zfs/{hostname}/snapshots/{snapshot_name}/clone`: Clone a ZFS snapshot.
*   `POST /zfs/{hostname}/snapshots/{snapshot_name}/send`: Send a ZFS snapshot to another location.
*   `POST /zfs/{hostname}/receive`: Receive a ZFS snapshot stream.
*   `GET /zfs/{hostname}/snapshots/{snapshot_name}/diff`: Show differences between snapshots.
*   `GET /zfs/{hostname}/health`: Get comprehensive ZFS health status.
*   `GET /zfs/{hostname}/arc-stats`: Get ZFS ARC (cache) statistics.
*   `GET /zfs/{hostname}/events`: Monitor ZFS events and system messages.
*   `GET /zfs/{hostname}/report`: Generate comprehensive ZFS system report.
*   `GET /zfs/{hostname}/snapshots/usage`: Analyze ZFS snapshot usage patterns.
*   `GET /zfs/{hostname}/optimize`: Get ZFS optimization recommendations.

## 🛠️ MCP Tools

The `fastmcp` server provides a powerful command-line interface for interacting with your infrastructure.

### Container Management

*   `list_containers`: List Docker containers on a specific device.
    *   `device` (str): The device to list containers on.
    *   `status` (str, optional): Filter by container status.
    *   `all_containers` (bool, optional): Include stopped containers.
    *   `timeout` (int, optional): The SSH timeout in seconds.
    *   `limit` (int, optional): The maximum number of containers to return.
    *   `offset` (int, optional): The number of containers to skip.
*   `get_container_info`: Get detailed information about a specific Docker container.
    *   `device` (str): The device the container is on.
    *   `container_name` (str): The name of the container.
    *   `timeout` (int, optional): The SSH timeout in seconds.
*   `get_container_logs`: Get logs from a specific Docker container.
    *   `device` (str): The device the container is on.
    *   `container_name` (str): The name of the container.
    *   `since` (str, optional): Show logs since a specific time.
    *   `tail` (int, optional): The number of lines to show from the end of the logs.
    *   `timeout` (int, optional): The SSH timeout in seconds.
*   `start_container`: Start a Docker container on a specific device.
    *   `device` (str): The device the container is on.
    *   `container_name` (str): The name of the container to start.
    *   `timeout` (int, optional): The SSH timeout in seconds.
*   `stop_container`: Stop a Docker container on a specific device.
    *   `device` (str): The device the container is on.
    *   `container_name` (str): The name of the container to stop.
    *   `force` (bool, optional): Force stop the container.
    *   `timeout` (int, optional): The SSH timeout in seconds.
*   `restart_container`: Restart a Docker container on a specific device.
    *   `device` (str): The device the container is on.
    *   `container_name` (str): The name of the container to restart.
    *   `timeout` (int, optional): The SSH timeout in seconds.
*   `remove_container`: Remove a Docker container on a specific device.
    *   `device` (str): The device the container is on.
    *   `container_name` (str): The name of the container to remove.
    *   `force` (bool, optional): Force remove the container.
    *   `remove_volumes` (bool, optional): Remove associated volumes.
    *   `timeout` (int, optional): The SSH timeout in seconds.
*   `get_container_stats`: Get real-time resource usage statistics for a Docker container.
    *   `device` (str): The device the container is on.
    *   `container_name` (str): The name of the container.
    *   `timeout` (int, optional): The SSH timeout in seconds.
*   `execute_in_container`: Execute a command inside a Docker container.
    *   `device` (str): The device the container is on.
    *   `container_name` (str): The name of the container.
    *   `command` (str): The command to execute.
    *   `user` (str, optional): User to execute command as.
    *   `workdir` (str, optional): Working directory for command execution.
    *   `interactive` (bool, optional): Run in interactive mode.
    *   `timeout` (int, optional): The SSH timeout in seconds.

### System Monitoring

*   `get_drive_health`: Get S.M.A.R.T. drive health information and disk status.
    *   `device` (str): The device to get drive health from.
    *   `drive` (str, optional): The drive to get health information for.
    *   `timeout` (int, optional): The SSH timeout in seconds.
*   `get_drives_stats`: Get drive usage statistics, I/O performance, and utilization metrics.
    *   `device` (str): The device to get drive stats from.
    *   `drive` (str, optional): The drive to get stats for.
    *   `timeout` (int, optional): The SSH timeout in seconds.
*   `get_system_logs`: Get system logs from journald or traditional syslog.
    *   `device` (str): The device to get system logs from.
    *   `service` (str, optional): The service to get logs for.
    *   `since` (str, optional): Show logs since a specific time.
    *   `lines` (int, optional): The number of lines to return.
    *   `timeout` (int, optional): The SSH timeout in seconds.

### Device Management

*   `list_devices`: List all registered infrastructure devices.
*   `add_device`: Add a new device to the infrastructure registry.
    *   `hostname` (str): The hostname of the device.
    *   `device_type` (str, optional): The type of the device.
    *   `description` (str, optional): A description of the device.
    *   `location` (str, optional): The location of the device.
    *   `monitoring_enabled` (bool, optional): Whether monitoring is enabled for the device.
    *   `ip_address` (str, optional): The IP address of the device.
    *   `ssh_port` (int, optional): The SSH port of the device.
    *   `ssh_username` (str, optional): The SSH username for the device.
    *   `tags` (dict, optional): A dictionary of tags for the device.
*   `remove_device`: Remove a device from the infrastructure registry.
    *   `hostname` (str): The hostname of the device to remove.
*   `edit_device`: Edit/update details of an existing device in the infrastructure registry.
    *   `hostname` (str): The hostname of the device to edit.
    *   `device_type` (str, optional): The new device type.
    *   `description` (str, optional): The new description.
    *   `location` (str, optional): The new location.
    *   `monitoring_enabled` (bool, optional): The new monitoring status.
    *   `ip_address` (str, optional): The new IP address.
    *   `ssh_port` (int, optional): The new SSH port.
    *   `ssh_username` (str, optional): The new SSH username.
    *   `tags` (dict, optional): The new tags.

### Proxy Configuration Management

*   `list_proxy_configs`: List SWAG reverse proxy configurations with real-time sync check.
*   `get_proxy_config`: Get specific proxy configuration with real-time file content.
*   `scan_proxy_configs`: Scan proxy configuration directory for fresh configs and sync to database.
*   `sync_proxy_config`: Sync specific proxy configuration with file system.
*   `get_proxy_config_summary`: Get summary statistics for proxy configurations.

### Docker Compose Deployment

*   `modify_compose_for_device`: Modify docker-compose content for deployment on target device.
    *   `compose_content` (str): Original docker-compose.yml content.
    *   `target_device` (str): Target device hostname.
    *   `service_name` (str, optional): Specific service to modify.
    *   `update_appdata_paths` (bool, optional): Update volume paths to device appdata path.
    *   `auto_assign_ports` (bool, optional): Automatically assign available ports.
    *   `generate_proxy_configs` (bool, optional): Generate SWAG proxy configurations.
*   `deploy_compose_to_device`: Deploy docker-compose content to target device.
    *   `device` (str): Target device hostname.
    *   `compose_content` (str): Docker compose content to deploy.
    *   `deployment_path` (str): Path where to store compose file on device.
    *   `start_services` (bool, optional): Start services after deployment.
    *   `pull_images` (bool, optional): Pull latest images before starting.
*   `modify_and_deploy_compose`: Modify and deploy docker-compose in a single operation.
*   `scan_device_ports`: Scan for available ports on target device.
*   `scan_docker_networks`: Scan Docker networks on target device.
*   `generate_proxy_config`: Generate SWAG reverse proxy configuration for a specific service.

### ZFS Management

*   `list_zfs_pools`: List all ZFS pools on a device.
    *   `device` (str): The device hostname.
    *   `timeout` (int, optional): SSH timeout in seconds.
*   `get_zfs_pool_status`: Get detailed status for a specific ZFS pool.
    *   `device` (str): The device hostname.
    *   `pool_name` (str): ZFS pool name.
    *   `timeout` (int, optional): SSH timeout in seconds.
*   `list_zfs_datasets`: List ZFS datasets, optionally filtered by pool.
    *   `device` (str): The device hostname.
    *   `pool_name` (str, optional): Filter by pool name.
    *   `timeout` (int, optional): SSH timeout in seconds.
*   `get_zfs_dataset_properties`: Get all properties for a specific ZFS dataset.
    *   `device` (str): The device hostname.
    *   `dataset_name` (str): Dataset name.
    *   `timeout` (int, optional): SSH timeout in seconds.
*   `list_zfs_snapshots`: List ZFS snapshots, optionally filtered by dataset.
    *   `device` (str): The device hostname.
    *   `dataset_name` (str, optional): Filter by dataset name.
    *   `timeout` (int, optional): SSH timeout in seconds.
*   `create_zfs_snapshot`: Create a new ZFS snapshot.
    *   `device` (str): The device hostname.
    *   `dataset_name` (str): Dataset name to snapshot.
    *   `snapshot_name` (str): Snapshot name.
    *   `recursive` (bool, optional): Create recursive snapshot.
    *   `timeout` (int, optional): SSH timeout in seconds.
*   `clone_zfs_snapshot`: Clone a ZFS snapshot.
    *   `device` (str): The device hostname.
    *   `snapshot_name` (str): Snapshot name to clone.
    *   `clone_name` (str): Name for the cloned dataset.
    *   `timeout` (int, optional): SSH timeout in seconds.
*   `send_zfs_snapshot`: Send a ZFS snapshot for replication/backup.
    *   `device` (str): The device hostname.
    *   `snapshot_name` (str): Snapshot name to send.
    *   `destination` (str, optional): Destination for snapshot send.
    *   `incremental` (bool, optional): Use incremental send.
    *   `timeout` (int, optional): SSH timeout in seconds.
*   `receive_zfs_snapshot`: Receive a ZFS snapshot stream.
    *   `device` (str): The device hostname.
    *   `dataset_name` (str): Dataset name for receiving snapshot.
    *   `timeout` (int, optional): SSH timeout in seconds.
*   `diff_zfs_snapshots`: Compare differences between two ZFS snapshots.
    *   `device` (str): The device hostname.
    *   `snapshot1` (str): First snapshot name.
    *   `snapshot2` (str): Second snapshot name.
    *   `timeout` (int, optional): SSH timeout in seconds.
*   `check_zfs_health`: Comprehensive ZFS health check.
    *   `device` (str): The device hostname.
    *   `timeout` (int, optional): SSH timeout in seconds.
*   `get_zfs_arc_stats`: Get ZFS ARC (Adaptive Replacement Cache) statistics.
    *   `device` (str): The device hostname.
    *   `timeout` (int, optional): SSH timeout in seconds.
*   `monitor_zfs_events`: Monitor ZFS events and error messages.
    *   `device` (str): The device hostname.
    *   `timeout` (int, optional): SSH timeout in seconds.
*   `generate_zfs_report`: Generate comprehensive ZFS report.
    *   `device` (str): The device hostname.
    *   `timeout` (int, optional): SSH timeout in seconds.
*   `analyze_snapshot_usage`: Analyze snapshot space usage and provide cleanup recommendations.
    *   `device` (str): The device hostname.
    *   `timeout` (int, optional): SSH timeout in seconds.
*   `optimize_zfs_settings`: Analyze ZFS configuration and suggest optimizations.
    *   `device` (str): The device hostname.
    *   `timeout` (int, optional): SSH timeout in seconds.

### Comprehensive Device Info

*   `get_device_info`: Get comprehensive device information including capabilities analysis and system metrics.

## 🔗 MCP Resources

The `fastmcp` server provides MCP resources for programmatic access to infrastructure data through Claude Desktop and other MCP clients.

### Infrastructure Resources

*   `infra://devices`: List all registered infrastructure devices.
*   `infra://{device}/status`: Get comprehensive device status and metrics.

### Docker Compose Resources

*   `docker://configs`: Global listing of all Docker Compose configurations.
*   `docker://{device}/stacks`: List all Docker Compose stacks on a device.
*   `docker://{device}/{service}`: Get Docker Compose configuration for a service.

### SWAG Proxy Resources

*   `swag://configs`: List all SWAG reverse proxy configurations.
*   `swag://{service_name}`: Get SWAG service configuration content.
*   `swag://{device}/{path}`: Get SWAG device-specific resource content.

### ZFS Resources

*   `zfs://pools/{hostname}`: Get all ZFS pools for a device.
*   `zfs://pools/{hostname}/{pool_name}`: Get specific ZFS pool status.
*   `zfs://datasets/{hostname}`: Get all ZFS datasets for a device.
*   `zfs://snapshots/{hostname}`: Get ZFS snapshots for a device.
*   `zfs://health/{hostname}`: Get ZFS health status for a device.

**Example Usage:**
```
zfs://pools/squirts
zfs://snapshots/squirts?limit=100
zfs://health/squirts
```

## 🗄️ Database Schema

`infrastructor` uses a TimescaleDB database to store time-series data for infrastructure monitoring. The schema is designed to be flexible and extensible, and it includes tables for:

*   **`devices`:** A registry of all infrastructure devices.
*   **`system_metrics`:** Time-series data for system-level metrics (CPU, memory, disk, etc.).
*   **`drive_health`:** Time-series data for S.M.A.R.T. drive health.
*   **`container_snapshots`:** Time-series data for Docker container metrics.
*   **`proxy_configs`:** SWAG reverse proxy configuration management.

The schema also makes extensive use of TimescaleDB's features, including:

*   **Hypertables:** For efficient storage and querying of time-series data.
*   **Compression Policies:** To automatically compress old data and save storage space.
*   **Continuous Aggregates:** To pre-calculate hourly and daily summaries of the time-series data for faster querying.

## 👨‍💻 Development

`infrastructor` uses a modern set of development tools and practices to ensure code quality and maintainability.

*   **Linting and Formatting:** `ruff` is used for linting and formatting the code.
*   **Type Checking:** `mypy` is used for static type checking.
*   **Testing:** `pytest` is used for testing the code.

To run the tests, use the following command:

```bash
pytest
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## 📄 License

`infrastructor` is licensed under the MIT License. See the `LICENSE` file for more information.
