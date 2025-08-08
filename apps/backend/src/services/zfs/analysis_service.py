"""
ZFS Analysis Service

Handles ZFS analysis operations including reporting, optimization recommendations,
and snapshot usage analysis.
"""

from datetime import UTC, datetime
import logging

from typing import Any

from apps.backend.src.core.exceptions import ZFSError

from .base import ZFSBaseService
from .dataset_service import ZFSDatasetService
from .health_service import ZFSHealthService
from .pool_service import ZFSPoolService
from .snapshot_service import ZFSSnapshotService

logger = logging.getLogger(__name__)


class ZFSAnalysisService(ZFSBaseService):
    """Service for ZFS analysis and reporting operations"""

    def __init__(self) -> None:
        super().__init__()
        self.pool_service = ZFSPoolService()
        self.dataset_service = ZFSDatasetService()
        self.snapshot_service = ZFSSnapshotService()
        self.health_service = ZFSHealthService()

    async def generate_zfs_report(self, hostname: str, timeout: int = 120) -> dict[str, Any]:
        """Generate comprehensive ZFS report"""
        try:
            # Gather all ZFS information
            pools = await self.pool_service.list_pools(hostname, timeout)
            datasets = await self.dataset_service.list_datasets(hostname, None, timeout)
            snapshots = await self.snapshot_service.list_snapshots(hostname, None, timeout)
            health = await self.health_service.check_zfs_health(hostname, timeout)
            arc_stats = await self.health_service.get_arc_stats(hostname, timeout)

            # Calculate summary statistics
            total_pools = len(pools)
            total_datasets = len(datasets)
            total_snapshots = len(snapshots)

            return {
                "hostname": hostname,
                "summary": {
                    "total_pools": total_pools,
                    "total_datasets": total_datasets,
                    "total_snapshots": total_snapshots,
                    "overall_health": health["overall_health"],
                },
                "pools": pools,
                "datasets": datasets,
                "snapshots": snapshots,
                "health_check": health,
                "arc_statistics": arc_stats,
                "generated_at": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error generating ZFS report for {hostname}: {e}")
            raise ZFSError(
                f"Failed to generate ZFS report: {str(e)}",
                operation="generate_report",
                hostname=hostname,
            )

    async def analyze_snapshot_usage(self, hostname: str, timeout: int = 60) -> dict[str, Any]:
        """Analyze snapshot space usage and provide cleanup recommendations"""
        try:
            snapshots = await self.snapshot_service.list_snapshots(hostname, None, timeout)

            # Analyze snapshot usage patterns
            usage_analysis: dict[str, Any] = {
                "total_snapshots": len(snapshots),
                "snapshots_by_dataset": {},
                "largest_snapshots": [],
                "oldest_snapshots": [],
                "cleanup_recommendations": [],
            }

            # Group by dataset
            for snapshot in snapshots:
                dataset_name = snapshot["name"].split("@")[0]
                if dataset_name not in usage_analysis["snapshots_by_dataset"]:
                    usage_analysis["snapshots_by_dataset"][dataset_name] = []
                usage_analysis["snapshots_by_dataset"][dataset_name].append(snapshot)

            # Find largest snapshots (sort by used space if numeric)
            try:
                sorted_snapshots = sorted(
                    snapshots, key=lambda x: self._parse_size(x["used"]), reverse=True
                )
                usage_analysis["largest_snapshots"] = sorted_snapshots[:10]
            except:
                usage_analysis["largest_snapshots"] = snapshots[:10]

            # Add cleanup recommendations
            for dataset, dataset_snapshots in usage_analysis["snapshots_by_dataset"].items():
                if len(dataset_snapshots) > 50:
                    usage_analysis["cleanup_recommendations"].append(
                        f"Dataset {dataset} has {len(dataset_snapshots)} snapshots - consider cleanup"
                    )

            usage_analysis["analyzed_at"] = datetime.now(UTC).isoformat()
            return usage_analysis

        except Exception as e:
            self.logger.error(f"Error analyzing snapshot usage on {hostname}: {e}")
            raise ZFSError(
                f"Failed to analyze snapshot usage: {str(e)}",
                operation="analyze_snapshot_usage",
                hostname=hostname,
            )

    async def optimize_zfs_settings(self, hostname: str, timeout: int = 60) -> dict[str, Any]:
        """Analyze ZFS configuration and suggest optimizations"""
        try:
            # Get ARC stats for memory optimization
            arc_stats = await self.health_service.get_arc_stats(hostname, timeout)

            # Get pool properties for optimization analysis
            pools = await self.pool_service.list_pools(hostname, timeout)

            recommendations = []

            # Analyze ARC hit ratio
            hit_ratio = arc_stats.get("hit_ratio_percent", 0)
            if hit_ratio < 80:
                recommendations.append(
                    {
                        "type": "performance",
                        "priority": "high",
                        "issue": f"Low ARC hit ratio: {hit_ratio}%",
                        "recommendation": "Consider increasing ARC size or investigating memory pressure",
                    }
                )

            # Analyze pool capacity
            for pool in pools:
                capacity = (
                    float(pool["capacity"]) if pool["capacity"].replace(".", "").isdigit() else 0
                )
                if capacity > 80:
                    recommendations.append(
                        {
                            "type": "capacity",
                            "priority": "high" if capacity > 90 else "medium",
                            "issue": f"Pool {pool['name']} is {capacity}% full",
                            "recommendation": "Consider adding storage or cleaning up old data",
                        }
                    )

            return {
                "hostname": hostname,
                "current_arc_stats": arc_stats,
                "pool_status": pools,
                "recommendations": recommendations,
                "analyzed_at": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error optimizing ZFS settings on {hostname}: {e}")
            raise ZFSError(
                f"Failed to optimize ZFS settings: {str(e)}",
                operation="optimize_settings",
                hostname=hostname,
            )

    async def get_dataset_usage_trends(
        self, hostname: str, dataset_name: str, timeout: int = 60
    ) -> dict[str, Any]:
        """Analyze dataset usage trends and growth patterns"""
        try:
            # Get current dataset properties
            dataset_props = await self.dataset_service.get_dataset_properties(
                hostname, dataset_name, timeout
            )

            # Get snapshots for this dataset
            snapshots = await self.snapshot_service.list_snapshots(hostname, dataset_name, timeout)

            # Analyze growth patterns (simplified - in production you'd want historical data)
            return {
                "dataset_name": dataset_name,
                "current_properties": dataset_props,
                "snapshot_count": len(snapshots),
                "recent_snapshots": snapshots[:5],  # Last 5 snapshots
                "analyzed_at": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            self.logger.error(
                f"Error analyzing dataset usage trends for {dataset_name} on {hostname}: {e}"
            )
            raise ZFSError(
                f"Failed to analyze dataset usage trends: {str(e)}",
                operation="get_dataset_usage_trends",
                hostname=hostname,
            )

    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes for comparison"""
        if not size_str or size_str == "-":
            return 0

        size_str = size_str.strip().upper()
        
        # Define multipliers
        multipliers = {
            "B": 1,
            "K": 1024,
            "M": 1024**2,
            "G": 1024**3,
            "T": 1024**4,
            "P": 1024**5,
            "E": 1024**6,
        }

        # Try to extract number and unit
        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                try:
                    value = float(size_str[:-1]) if suffix != "B" else float(size_str[:-1])
                    return int(value * multiplier)
                except ValueError:
                    continue

        # Try to parse as plain number
        try:
            return int(float(size_str))
        except ValueError:
            return 0
