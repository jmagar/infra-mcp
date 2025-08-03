"""
Docker Compose Configuration MCP Resources

MCP resources for exposing Docker Compose configurations
with real-time file access and database integration.
"""

from __future__ import annotations

import logging
import json
import shlex
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

from apps.backend.src.utils.compose_parser import DockerComposeParser, ComposeParseError
from apps.backend.src.utils.ssh_client import execute_ssh_command_simple
from apps.backend.src.core.database import get_async_session
from apps.backend.src.models.device import Device
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def get_compose_config_resource(uri: str) -> dict[str, Any]:
    """
    Get Docker Compose configuration resource content

    Resource URI formats:
    - docker://device/service - Direct access to service compose file
    - docker://device/stacks - List all compose stacks on device
    - docker://configs - Global listing of all compose files

    Args:
        uri: Resource URI

    Returns:
        Dict containing resource content
    """
    try:
        parsed_uri = urlparse(uri)
        device = parsed_uri.netloc
        path = parsed_uri.path.lstrip("/")
        query_params = parse_qs(parsed_uri.query)

        # Extract options
        force_refresh = query_params.get("force_refresh", ["false"])[0].lower() == "true"
        include_parsed = query_params.get("include_parsed", ["true"])[0].lower() == "true"
        format_type = query_params.get("format", ["raw"])[0]  # raw, json

        # Handle different URI patterns
        if not device:
            raise ValueError(
                "Invalid Docker URI format. Use: docker://device/service or docker://configs"
            )

        # Pattern 1: docker://configs - Global listing
        if device == "configs" and not path:
            return await _get_global_compose_listing()

        # Pattern 2: docker://device/stacks - Device stacks listing
        elif path == "stacks":
            return await _get_device_compose_stacks(device)

        # Pattern 3: docker://device/service - Service compose file
        elif path and path != "stacks":
            service_name = path
            return await _get_service_compose_resource(
                device, service_name, force_refresh, include_parsed, format_type
            )

        else:
            raise ValueError(
                f"Unknown Docker URI format: {uri}. Use docker://device/service, docker://device/stacks, or docker://configs"
            )

    except Exception as e:
        logger.error(f"Error getting compose config resource {uri}: {e}")
        return {
            "error": str(e),
            "uri": uri,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resource_type": "error",
        }


async def _get_service_compose_resource(
    device: str,
    service_name: str,
    force_refresh: bool = False,
    include_parsed: bool = True,
    format_type: str = "raw",
) -> dict[str, Any]:
    """Get service compose configuration with path resolution"""

    try:
        # Step 1: Try to find compose file path via multiple methods
        compose_file_path = await _resolve_compose_file_path(device, service_name)

        if not compose_file_path:
            return {
                "error": f"Docker Compose file not found for service {service_name}",
                "service_name": service_name,
                "device": device,
                "searched_methods": [
                    "running_container_inspect",
                    "database_device_paths",
                    "common_path_patterns",
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "resource_type": "service_not_found",
            }

        # Step 2: Get file info and content via SSH
        file_info = await _get_file_info(device, compose_file_path)

        if not file_info.get("exists", False):
            return {
                "error": "Compose file path resolved but file does not exist",
                "service_name": service_name,
                "device": device,
                "file_path": compose_file_path,
                "file_info": file_info,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "resource_type": "file_not_found",
            }

        # Step 3: Read file content
        content = await _get_file_content(device, compose_file_path)

        if content is None:
            return {
                "error": "Failed to read compose file content",
                "service_name": service_name,
                "device": device,
                "file_path": compose_file_path,
                "file_info": file_info,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "resource_type": "read_error",
            }

        # Step 4: Build basic resource data
        resource_data = {
            "uri": f"docker://{device}/{service_name}",
            "service_name": service_name,
            "device": device,
            "file_path": compose_file_path,
            "file_name": Path(compose_file_path).name,
            "file_info": file_info,
            "content_length": len(content),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resource_type": "docker_compose_service",
            "format": format_type,
        }

        # Step 5: Format content based on requested format
        if format_type == "raw":
            resource_data["content"] = content
            resource_data["mime_type"] = "text/yaml"

        elif format_type == "json":
            resource_data["raw_content"] = content
            resource_data["mime_type"] = "application/json"

        # Step 6: Parse compose content if requested
        if include_parsed:
            try:
                parser = DockerComposeParser()
                parsed_config = parser.parse_compose_content(content, compose_file_path)
                resource_data["parsed_config"] = parsed_config
                resource_data["services_list"] = list(parsed_config.get("services", {}).keys())

                # Add service-specific info if this service exists in the compose file
                services = parsed_config.get("services", {})
                if service_name in services:
                    resource_data["service_config"] = services[service_name]
                else:
                    # Find similar service names
                    similar_services = [
                        s
                        for s in services.keys()
                        if service_name.lower() in s.lower() or s.lower() in service_name.lower()
                    ]
                    resource_data["service_found_in_compose"] = False
                    resource_data["available_services"] = list(services.keys())
                    resource_data["similar_services"] = similar_services

            except ComposeParseError as e:
                resource_data["parse_error"] = str(e)
                logger.error(f"Failed to parse compose file {compose_file_path}: {e}")

        return resource_data

    except Exception as e:
        logger.error(f"Error getting service compose resource for {service_name}: {e}")
        return {
            "error": str(e),
            "service_name": service_name,
            "device": device,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resource_type": "service_error",
        }


async def _resolve_compose_file_path(device: str, service_name: str) -> Optional[str]:
    """
    Resolve the compose file path for a service using multiple methods:
    1. Check running containers for compose file labels
    2. Use database device paths + common patterns
    3. Search common locations
    """

    # Method 1: Check running containers
    logger.info(
        f"Resolving compose path for {service_name} on {device} - checking running containers"
    )

    try:
        # Get running containers with compose labels
        docker_ps_cmd = """
        docker ps --format '{{json .}}' --filter "label=com.docker.compose.service" | head -20
        """

        result = await execute_ssh_command_simple(device, docker_ps_cmd, timeout=30)

        if result.return_code == 0:
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue

                try:
                    container_info = json.loads(line)
                    container_name = container_info.get("Names", "")

                    # Check if this container matches our service
                    if service_name.lower() in container_name.lower():
                        # Get detailed container info
                        inspect_cmd = f"docker inspect {shlex.quote(container_name)}"
                        inspect_result = await execute_ssh_command_simple(
                            device, inspect_cmd, timeout=15
                        )

                        if inspect_result.return_code == 0:
                            inspect_data = json.loads(inspect_result.stdout)
                            if inspect_data:
                                labels = inspect_data[0].get("Config", {}).get("Labels", {})
                                config_files = labels.get("com.docker.compose.project.config_files")

                                if config_files:
                                    # config_files can be comma-separated list
                                    file_paths = [f.strip() for f in config_files.split(",")]
                                    if file_paths:
                                        logger.info(
                                            f"Found compose file via container labels: {file_paths[0]}"
                                        )
                                        return file_paths[0]

                except json.JSONDecodeError:
                    continue

    except Exception as e:
        logger.warning(f"Error checking running containers for {service_name}: {e}")

    # Method 2: Database device paths + common patterns
    logger.info(f"Checking database paths for {device}")

    try:
        async with get_async_session() as session:
            query = select(Device).where(Device.hostname == device)
            result = await session.execute(query)
            device_record = result.scalar_one_or_none()

            if device_record:
                search_paths = []

                # Add primary paths from database
                if device_record.docker_compose_path:
                    search_paths.append(device_record.docker_compose_path)

                if device_record.docker_appdata_path:
                    search_paths.append(device_record.docker_appdata_path)

                # Add additional paths from tags
                all_compose_paths = device_record.tags.get("all_docker_compose_paths", [])
                search_paths.extend(all_compose_paths)

                all_appdata_paths = device_record.tags.get("appdata_paths", [])
                search_paths.extend(all_appdata_paths)

                # Try to find compose file in these paths
                for base_path in search_paths:
                    compose_path = await _search_compose_file_in_path(
                        device, service_name, base_path
                    )
                    if compose_path:
                        logger.info(f"Found compose file via database paths: {compose_path}")
                        return compose_path

    except Exception as e:
        logger.warning(f"Error checking database paths for {device}: {e}")

    # Method 3: Common path patterns search
    logger.info(f"Searching common paths for {service_name}")

    common_base_paths = ["/mnt/appdata", "/opt/docker", "/home/docker", "/docker", "/srv/docker"]

    for base_path in common_base_paths:
        compose_path = await _search_compose_file_in_path(device, service_name, base_path)
        if compose_path:
            logger.info(f"Found compose file via common paths: {compose_path}")
            return compose_path

    logger.warning(f"Could not resolve compose file path for {service_name} on {device}")
    return None


async def _search_compose_file_in_path(
    device: str, service_name: str, base_path: str
) -> Optional[str]:
    """Search for compose file in a specific base path"""

    # Common compose file patterns
    compose_patterns = [
        f"{base_path}/{service_name}/docker-compose.yml",
        f"{base_path}/{service_name}/docker-compose.yaml",
        f"{base_path}/{service_name}/compose.yml",
        f"{base_path}/{service_name}/compose.yaml",
        f"{base_path}/docker-compose.yml",
        f"{base_path}/docker-compose.yaml",
    ]

    # Try each pattern
    for pattern in compose_patterns:
        try:
            file_info = await _get_file_info(device, pattern)
            if file_info.get("exists"):
                return pattern
        except Exception:
            continue

    # Fallback: search for any compose files in the directory
    try:
        search_cmd = f"""
        find {shlex.quote(base_path)} -name "docker-compose.y*ml" -o -name "compose.y*ml" | grep -i {shlex.quote(service_name)} | head -1
        """

        result = await execute_ssh_command_simple(device, search_cmd, timeout=15)

        if result.return_code == 0 and result.stdout.strip():
            found_path = result.stdout.strip().split("\n")[0]
            if found_path:
                return found_path

    except Exception:
        pass

    return None


async def _get_file_info(device: str, file_path: str) -> dict[str, Any]:
    """Get file information via SSH"""

    try:
        stat_cmd = f"stat -c '%n|%s|%Y|%A' {shlex.quote(file_path)} 2>/dev/null || echo 'NOT_FOUND'"

        result = await execute_ssh_command_simple(device, stat_cmd, timeout=10)

        if result.return_code == 0 and result.stdout.strip() != "NOT_FOUND":
            parts = result.stdout.strip().split("|")
            if len(parts) >= 4:
                return {
                    "exists": True,
                    "file_path": parts[0],
                    "file_size": int(parts[1]),
                    "last_modified": datetime.fromtimestamp(
                        int(parts[2]), tz=timezone.utc
                    ).isoformat(),
                    "permissions": parts[3],
                    "readable": "r" in parts[3],
                }

        return {"exists": False, "file_path": file_path}

    except Exception as e:
        logger.error(f"Error getting file info for {file_path} on {device}: {e}")
        return {"exists": False, "file_path": file_path, "error": str(e)}


async def _get_file_content(device: str, file_path: str) -> Optional[str]:
    """Get file content via SSH"""

    try:
        cat_cmd = f"cat {shlex.quote(file_path)}"

        result = await execute_ssh_command_simple(device, cat_cmd, timeout=30)

        if result.return_code == 0:
            return result.stdout
        else:
            logger.error(f"Failed to read file {file_path} on {device}: {result.stderr}")
            return None

    except Exception as e:
        logger.error(f"Error reading file {file_path} on {device}: {e}")
        return None


async def _get_device_compose_stacks(device: str) -> dict[str, Any]:
    """Get list of all compose stacks on a device"""

    try:
        # Get running compose stacks
        running_stacks = await _get_running_compose_stacks(device)

        # Get discovered compose files from database paths
        discovered_stacks = await _get_discovered_compose_files(device)

        # Combine and deduplicate
        all_stacks = {}

        # Add running stacks
        for stack in running_stacks:
            stack_name = stack["stack_name"]
            all_stacks[stack_name] = {**stack, "status": "running", "source": "docker_ps"}

        # Add discovered files
        for stack in discovered_stacks:
            stack_name = stack["stack_name"]
            if stack_name in all_stacks:
                # Merge information
                all_stacks[stack_name]["compose_file"] = stack["compose_file"]
                all_stacks[stack_name]["discovered"] = True
            else:
                all_stacks[stack_name] = {**stack, "status": "discovered", "source": "filesystem"}

        return {
            "uri": f"docker://{device}/stacks",
            "device": device,
            "total_stacks": len(all_stacks),
            "running_stacks": len([s for s in all_stacks.values() if s["status"] == "running"]),
            "discovered_stacks": len(
                [s for s in all_stacks.values() if s["status"] == "discovered"]
            ),
            "stacks": list(all_stacks.values()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resource_type": "docker_compose_stacks",
        }

    except Exception as e:
        logger.error(f"Error getting compose stacks for {device}: {e}")
        return {
            "error": str(e),
            "device": device,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resource_type": "stacks_error",
        }


async def _get_running_compose_stacks(device: str) -> list[dict[str, Any]]:
    """Get running compose stacks from docker ps"""

    stacks = []

    try:
        # Get containers with compose labels
        docker_ps_cmd = """
        docker ps --format '{{json .}}' --filter "label=com.docker.compose.project"
        """

        result = await execute_ssh_command_simple(device, docker_ps_cmd, timeout=30)

        if result.return_code == 0:
            project_stacks = {}

            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue

                try:
                    container_info = json.loads(line)
                    container_name = container_info.get("Names", "")

                    # Get compose labels via inspect
                    inspect_cmd = f"docker inspect {shlex.quote(container_name)}"
                    inspect_result = await execute_ssh_command_simple(
                        device, inspect_cmd, timeout=10
                    )

                    if inspect_result.return_code == 0:
                        inspect_data = json.loads(inspect_result.stdout)
                        if inspect_data:
                            labels = inspect_data[0].get("Config", {}).get("Labels", {})

                            project_name = labels.get("com.docker.compose.project")
                            service_name = labels.get("com.docker.compose.service")
                            config_files = labels.get("com.docker.compose.project.config_files")

                            if project_name:
                                if project_name not in project_stacks:
                                    project_stacks[project_name] = {
                                        "stack_name": project_name,
                                        "services": [],
                                        "compose_files": [],
                                        "containers": [],
                                    }

                                if service_name:
                                    project_stacks[project_name]["services"].append(service_name)

                                if config_files:
                                    files = [f.strip() for f in config_files.split(",")]
                                    project_stacks[project_name]["compose_files"].extend(files)

                                project_stacks[project_name]["containers"].append(
                                    {
                                        "name": container_name,
                                        "service": service_name,
                                        "status": container_info.get("Status", ""),
                                        "image": container_info.get("Image", ""),
                                    }
                                )

                except json.JSONDecodeError:
                    continue

            # Clean up and deduplicate
            for project_name, stack_info in project_stacks.items():
                stack = {
                    "stack_name": project_name,
                    "services": list(set(stack_info["services"])),
                    "compose_files": list(set(stack_info["compose_files"])),
                    "total_containers": len(stack_info["containers"]),
                    "containers": stack_info["containers"],
                    "resource_uri": f"docker://{device}/{project_name}",
                }

                if stack["compose_files"]:
                    stack["primary_compose_file"] = stack["compose_files"][0]

                stacks.append(stack)

    except Exception as e:
        logger.error(f"Error getting running compose stacks for {device}: {e}")

    return stacks


async def _get_discovered_compose_files(device: str) -> list[dict[str, Any]]:
    """Get discovered compose files from database paths"""

    discovered = []

    try:
        async with get_async_session() as session:
            query = select(Device).where(Device.hostname == device)
            result = await session.execute(query)
            device_record = result.scalar_one_or_none()

            if not device_record:
                return discovered

            search_paths = []

            if device_record.docker_compose_path:
                search_paths.append(device_record.docker_compose_path)

            if device_record.docker_appdata_path:
                search_paths.append(device_record.docker_appdata_path)

            all_compose_paths = device_record.tags.get("all_docker_compose_paths", [])
            search_paths.extend(all_compose_paths)

            # Search for compose files in each path
            for base_path in search_paths:
                try:
                    find_cmd = f"""
                    find {shlex.quote(base_path)} -name "docker-compose.y*ml" -o -name "compose.y*ml" | head -20
                    """

                    result = await execute_ssh_command_simple(device, find_cmd, timeout=20)

                    if result.return_code == 0:
                        for compose_file in result.stdout.strip().split("\n"):
                            if not compose_file.strip():
                                continue

                            # Extract stack name from path
                            path_obj = Path(compose_file)
                            stack_name = path_obj.parent.name

                            discovered.append(
                                {
                                    "stack_name": stack_name,
                                    "compose_file": compose_file,
                                    "directory": str(path_obj.parent),
                                    "filename": path_obj.name,
                                    "resource_uri": f"docker://{device}/{stack_name}",
                                }
                            )

                except Exception as e:
                    logger.warning(f"Error searching {base_path} on {device}: {e}")
                    continue

    except Exception as e:
        logger.error(f"Error getting discovered compose files for {device}: {e}")

    return discovered


async def _get_global_compose_listing() -> dict[str, Any]:
    """Get global listing of all compose configurations across all devices"""

    try:
        async with get_async_session() as session:
            query = select(Device).where(Device.monitoring_enabled.is_(True))
            result = await session.execute(query)
            devices = result.scalars().all()

            global_listing = {
                "uri": "docker://configs",
                "total_devices": len(devices),
                "devices": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "resource_type": "docker_compose_global",
            }

            # Get compose info for each device
            for device in devices:
                try:
                    device_stacks = await _get_device_compose_stacks(device.hostname)

                    device_info = {
                        "hostname": device.hostname,
                        "device_type": device.device_type,
                        "monitoring_enabled": device.monitoring_enabled,
                        "docker_compose_path": device.docker_compose_path,
                        "docker_appdata_path": device.docker_appdata_path,
                        "total_stacks": device_stacks.get("total_stacks", 0),
                        "running_stacks": device_stacks.get("running_stacks", 0),
                        "discovered_stacks": device_stacks.get("discovered_stacks", 0),
                        "stacks": device_stacks.get("stacks", []),
                        "resource_uri": f"docker://{device.hostname}/stacks",
                    }

                    global_listing["devices"].append(device_info)

                except Exception as e:
                    logger.error(f"Error getting stacks for device {device.hostname}: {e}")
                    device_info = {
                        "hostname": device.hostname,
                        "error": str(e),
                        "resource_uri": f"docker://{device.hostname}/stacks",
                    }
                    global_listing["devices"].append(device_info)

            # Calculate totals
            total_stacks = sum(d.get("total_stacks", 0) for d in global_listing["devices"])
            total_running = sum(d.get("running_stacks", 0) for d in global_listing["devices"])
            total_discovered = sum(d.get("discovered_stacks", 0) for d in global_listing["devices"])

            global_listing.update(
                {
                    "summary": {
                        "total_stacks_across_all_devices": total_stacks,
                        "total_running_stacks": total_running,
                        "total_discovered_stacks": total_discovered,
                        "devices_with_compose": len(
                            [d for d in global_listing["devices"] if d.get("total_stacks", 0) > 0]
                        ),
                    }
                }
            )

            return global_listing

    except Exception as e:
        logger.error(f"Error getting global compose listing: {e}")
        return {
            "error": str(e),
            "uri": "docker://configs",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resource_type": "global_error",
        }


async def list_compose_config_resources(device: str | None = None) -> list[dict[str, str]]:
    """
    List available compose configuration resources

    Args:
        device: Optional device filter

    Returns:
        List of resource descriptors
    """
    resources = []

    try:
        # Global resources
        resources.extend(
            [
                {
                    "uri": "docker://configs",
                    "name": "Docker Compose Global Configs",
                    "description": "Global listing of all Docker Compose configurations across all devices",
                    "mime_type": "application/json",
                }
            ]
        )

        # Device-specific resources
        if device:
            devices = [device]
        else:
            # Get all devices with docker capabilities from database
            async with get_async_session() as session:
                query = select(Device).where(Device.monitoring_enabled.is_(True))
                result = await session.execute(query)
                device_records = result.scalars().all()
                devices = [d.hostname for d in device_records if d.tags.get("docker_version")]

        for device_name in devices:
            # Device stacks listing
            resources.append(
                {
                    "uri": f"docker://{device_name}/stacks",
                    "name": f"Docker Stacks - {device_name}",
                    "description": f"List all Docker Compose stacks on {device_name}",
                    "mime_type": "application/json",
                }
            )

            # Try to discover services for individual service resources
            try:
                stacks_info = await _get_device_compose_stacks(device_name)

                for stack in stacks_info.get("stacks", []):
                    stack_name = stack["stack_name"]
                    resources.append(
                        {
                            "uri": f"docker://{device_name}/{stack_name}",
                            "name": f"{stack_name} Compose",
                            "description": f"Docker Compose configuration for {stack_name} on {device_name}",
                            "mime_type": "text/yaml",
                        }
                    )

            except Exception as e:
                logger.error(f"Error discovering services for {device_name}: {e}")

    except Exception as e:
        logger.error(f"Error listing compose config resources: {e}")

    return resources
