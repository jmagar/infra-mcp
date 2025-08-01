#  Infrastructor 🏗️

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/Framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![MCP](https://img.shields.io/badge/MCP-FastMCP-orange.svg)](https://pypi.org/project/fastmcp/)

**A comprehensive, API-driven infrastructure management and monitoring platform.**

`infrastructor` provides a powerful and flexible solution for managing and monitoring your entire infrastructure, from bare-metal servers to Docker containers. It combines a robust FastAPI backend with a flexible `fastmcp` server, giving you the power to manage your infrastructure through a REST API or a command-line interface.

## ✨ Features

*   **Comprehensive Monitoring:** Keep a close eye on all aspects of your infrastructure, including system metrics, drive health, container performance, and ZFS status.
*   **Container Management:** Easily manage your Docker containers with tools for listing, inspecting, and retrieving logs.
*   **Device Management:** Register and manage all of your infrastructure devices in a central location.
*   **Proxy Configuration Management:** Seamlessly manage your SWAG reverse proxy configurations.
*   **Time-Series Database:** `infrastructor` uses TimescaleDB to store and analyze time-series data, providing powerful insights into your infrastructure's performance over time.
*   **Dual-Interface:** Interact with your infrastructure through a powerful REST API or a flexible `fastmcp` command-line interface.

## 🏛️ Architecture

`infrastructor` uses a dual-server architecture:

*   **FastAPI REST API:** A robust backend that provides a RESTful interface for managing and monitoring your infrastructure.
*   **`fastmcp` Server:** A flexible command-line interface that acts as a client to the REST API, providing a powerful and scriptable way to interact with your infrastructure.

This architecture ensures that all operations, whether initiated from the API or the MCP, go through the same centralized logic, providing a consistent and reliable management experience.

```
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
    alembic upgrade head
    ```
6.  **Start the servers:**
    ```bash
    ./dev.sh start
    ```

## usage

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

### Comprehensive Device Info

*   `get_device_info`: Get comprehensive device information including capabilities analysis and system metrics.

## 🗄️ Database Schema

`infrastructor` uses a TimescaleDB database to store time-series data for infrastructure monitoring. The schema is designed to be flexible and extensible, and it includes tables for:

*   **`devices`:** A registry of all infrastructure devices.
*   **`system_metrics`:** Time-series data for system-level metrics (CPU, memory, disk, etc.).
*   **`drive_health`:** Time-series data for S.M.A.R.T. drive health.
*   **`container_snapshots`:** Time-series data for Docker container metrics.
*   **`zfs_status`:** Time-series data for ZFS pool and dataset status.
*   **`zfs_snapshots`:** Tracking of ZFS snapshots.
*   **`network_interfaces`:** Time-series data for network interface metrics.
*   **`docker_networks`:** Tracking of Docker networks.
*   **`backup_status`:** Tracking of backup jobs.
*   **`system_updates`:** Tracking of system updates.
*   **`vm_status`:** Time-series data for virtual machine metrics.
*   **`system_logs`:** Aggregation of system logs.

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
