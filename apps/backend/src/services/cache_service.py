"""
Cache Metadata Service

Service layer for managing cache metadata operations,
providing business logic for infrastructure data caching management.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.exceptions import DatabaseOperationError, ValidationError
from apps.backend.src.models.cache import CacheMetadata
from apps.backend.src.schemas.cache import (
    CacheMetadataCreate,
    CacheMetadataResponse,
    CacheMetadataList,
    CacheMetadataSummary,
    CacheMetrics,
    CachePerformanceAnalysis,
    CacheEfficiencyReport,
    CacheFilter,
)
from apps.backend.src.schemas.common import PaginationParams

logger = logging.getLogger(__name__)


class CacheService:
    """Service for managing cache metadata operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_cache_entry(
        self, cache_data: CacheMetadataCreate
    ) -> CacheMetadataResponse:
        """Create a new cache metadata entry."""
        try:
            cache_entry = CacheMetadata(
                cache_key=cache_data.cache_key,
                device_id=cache_data.device_id,
                data_type=cache_data.data_type,
                data_size_bytes=cache_data.data_size_bytes,
                created_at=cache_data.created_at or datetime.now(timezone.utc),
                last_accessed=cache_data.last_accessed or datetime.now(timezone.utc),
                access_count=cache_data.access_count or 0,
                hit_count=getattr(cache_data, 'hit_count', 0),
                miss_count=getattr(cache_data, 'miss_count', 0),
                ttl_seconds=cache_data.ttl_seconds,
                expires_at=cache_data.expires_at,
                cache_metadata=getattr(cache_data, 'metadata', {}),
            )

            self.db.add(cache_entry)
            await self.db.commit()
            await self.db.refresh(cache_entry)

            return CacheMetadataResponse.model_validate(cache_entry)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating cache entry: {e}")
            raise DatabaseOperationError(f"Failed to create cache entry: {str(e)}", "create_cache_entry")

    async def list_cache_entries(
        self,
        pagination: PaginationParams,
        cache_filter: Optional[CacheFilter] = None,
        hours: Optional[int] = None,
    ) -> CacheMetadataList:
        """List cache metadata entries with filtering and pagination."""
        try:
            query = select(CacheMetadata)

            # Apply filters
            if cache_filter:
                if cache_filter.device_ids:
                    query = query.where(CacheMetadata.device_id.in_(cache_filter.device_ids))

                if cache_filter.data_types:
                    query = query.where(CacheMetadata.data_type.in_(cache_filter.data_types))

                # cache_tier field may not exist in current schema
                # if cache_filter.cache_tiers:
                #     query = query.where(CacheMetadata.cache_tier.in_(cache_filter.cache_tiers))

                if cache_filter.expired_only:
                    query = query.where(CacheMetadata.expires_at < datetime.now(timezone.utc))

                if cache_filter.recently_accessed_only:
                    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
                    query = query.where(CacheMetadata.last_accessed >= cutoff)

                # hit_count/miss_count fields may not exist in current schema
                # if cache_filter.low_hit_ratio_only:
                #     # Filter entries with hit ratio < 50%
                #     query = query.where(
                #         (CacheMetadata.hit_count * 100.0 / (CacheMetadata.hit_count + CacheMetadata.miss_count)) < 50
                #     )

                if cache_filter.start_time:
                    query = query.where(CacheMetadata.created_at >= cache_filter.start_time)

                if cache_filter.end_time:
                    query = query.where(CacheMetadata.created_at <= cache_filter.end_time)

            # Apply time range filter
            if hours:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
                query = query.where(CacheMetadata.created_at >= cutoff_time)

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()

            # Apply ordering and pagination
            query = query.order_by(desc(CacheMetadata.created_at))
            query = query.offset(pagination.offset).limit(pagination.page_size)

            # Execute query
            result = await self.db.execute(query)
            cache_entries = result.scalars().all()

            # Convert to summary format
            summaries = []
            for entry in cache_entries:
                # Calculate hit ratio from actual hit_count/miss_count
                total_hits_misses = (entry.hit_count or 0) + (entry.miss_count or 0)
                hit_ratio = (entry.hit_count / total_hits_misses * 100) if total_hits_misses > 0 else 0
                
                summaries.append(
                    CacheMetadataSummary(
                        time=entry.created_at,
                        device_id=entry.device_id,
                        cache_key=entry.cache_key,
                        data_type=entry.data_type,
                        data_size_bytes=entry.data_size_bytes,
                        last_accessed=entry.last_accessed,
                        access_count=entry.access_count,
                        hit_ratio=hit_ratio,
                        cache_tier=getattr(entry, 'cache_tier', 'default'),
                        is_expired=entry.expires_at and entry.expires_at < datetime.now(timezone.utc),
                    )
                )

            total_pages = ((total_count - 1) // pagination.page_size) + 1 if total_count > 0 else 0
            
            return CacheMetadataList(
                items=summaries,
                total_count=total_count,
                page=pagination.page,
                page_size=pagination.page_size,
                total_pages=total_pages,
                has_next=pagination.page < total_pages,
                has_previous=pagination.page > 1,
            )

        except Exception as e:
            logger.error(f"Error listing cache entries: {e}")
            raise DatabaseOperationError(f"Failed to list cache entries: {str(e)}", "list_cache_entries")

    async def get_cache_entry(self, cache_key: str, device_id: Optional[UUID] = None) -> Optional[CacheMetadataResponse]:
        """Get a specific cache entry."""
        try:
            query = select(CacheMetadata).where(CacheMetadata.cache_key == cache_key)
            
            if device_id:
                query = query.where(CacheMetadata.device_id == device_id)

            result = await self.db.execute(query)
            cache_entry = result.scalar_one_or_none()

            if cache_entry:
                return CacheMetadataResponse.model_validate(cache_entry)
            return None

        except Exception as e:
            logger.error(f"Error getting cache entry {cache_key}: {e}")
            raise DatabaseOperationError(f"Failed to get cache entry: {str(e)}", "get_cache_entry")

    async def update_cache_access(self, cache_key: str, hit: bool, device_id: Optional[UUID] = None) -> bool:
        """Update cache access statistics."""
        try:
            query = select(CacheMetadata).where(CacheMetadata.cache_key == cache_key)
            
            if device_id:
                query = query.where(CacheMetadata.device_id == device_id)

            result = await self.db.execute(query)
            cache_entry = result.scalar_one_or_none()

            if not cache_entry:
                return False

            # Update access statistics
            cache_entry.access_count += 1
            cache_entry.last_accessed = datetime.now(timezone.utc)
            
            if hit:
                cache_entry.hit_count += 1
            else:
                cache_entry.miss_count += 1

            await self.db.commit()
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating cache access for {cache_key}: {e}")
            raise DatabaseOperationError(f"Failed to update cache access: {str(e)}", "update_cache_access")

    async def get_cache_metrics(
        self,
        device_ids: Optional[List[UUID]] = None,
        data_types: Optional[List[str]] = None,
        hours: int = 24,
    ) -> CacheMetrics:
        """Get aggregated cache metrics."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            period_start = cutoff_time
            period_end = datetime.now(timezone.utc)

            # Base query with time filter
            base_query = select(CacheMetadata).where(CacheMetadata.created_at >= cutoff_time)

            # Apply additional filters
            if device_ids:
                base_query = base_query.where(CacheMetadata.device_id.in_(device_ids))
            if data_types:
                base_query = base_query.where(CacheMetadata.data_type.in_(data_types))

            # Get total entries
            total_query = select(func.count()).select_from(base_query.subquery())
            total_result = await self.db.execute(total_query)
            total_entries = total_result.scalar()

            # Get aggregated metrics
            agg_query = select(
                func.sum(CacheMetadata.data_size_bytes),
                func.sum(CacheMetadata.access_count),
                func.sum(CacheMetadata.hit_count),
                func.sum(CacheMetadata.miss_count),
            ).select_from(base_query.subquery())

            agg_result = await self.db.execute(agg_query)
            agg_data = agg_result.fetchone()

            total_size_bytes = int(agg_data[0]) if agg_data[0] else 0
            total_accesses = int(agg_data[1]) if agg_data[1] else 0
            total_hits = int(agg_data[2]) if agg_data[2] else 0
            total_misses = int(agg_data[3]) if agg_data[3] else 0
            avg_compression_ratio = None  # Not tracked in current schema

            # Calculate rates
            cache_hit_rate = (total_hits / total_accesses * 100) if total_accesses > 0 else 0
            cache_miss_rate = (total_misses / total_accesses * 100) if total_accesses > 0 else 0

            # Count expired entries
            expired_query = select(func.count()).select_from(
                base_query.where(CacheMetadata.expires_at < datetime.now(timezone.utc)).subquery()
            )
            expired_result = await self.db.execute(expired_query)
            expired_entries = expired_result.scalar()

            # Get entries by tier - disabled as cache_tier not in current schema
            entries_by_tier = {"default": total_entries}

            # Get entries by data type
            data_type_query = (
                select(CacheMetadata.data_type, func.count())
                .select_from(base_query.subquery())
                .group_by(CacheMetadata.data_type)
                .order_by(desc(func.count()))
                .limit(10)
            )
            data_type_result = await self.db.execute(data_type_query)
            entries_by_data_type = dict(data_type_result.fetchall())

            # Get top accessed cache keys
            top_keys_query = (
                select(CacheMetadata.cache_key, func.sum(CacheMetadata.access_count))
                .select_from(base_query.subquery())
                .group_by(CacheMetadata.cache_key)
                .order_by(desc(func.sum(CacheMetadata.access_count)))
                .limit(10)
            )
            top_keys_result = await self.db.execute(top_keys_query)
            top_accessed_keys = [{"cache_key": row[0], "access_count": row[1]} for row in top_keys_result.fetchall()]

            return CacheMetrics(
                total_entries=total_entries,
                total_size_bytes=total_size_bytes,
                total_accesses=total_accesses,
                total_hits=total_hits,
                total_misses=total_misses,
                cache_hit_rate=cache_hit_rate,
                cache_miss_rate=cache_miss_rate,
                expired_entries=expired_entries,
                avg_compression_ratio=avg_compression_ratio,
                entries_by_tier=entries_by_tier,
                entries_by_data_type=entries_by_data_type,
                top_accessed_keys=top_accessed_keys,
                period_start=period_start,
                period_end=period_end,
            )

        except Exception as e:
            logger.error(f"Error getting cache metrics: {e}")
            raise DatabaseOperationError(f"Failed to get cache metrics: {str(e)}", "get_cache_metrics")

    async def get_cache_performance_analysis(
        self, data_type: Optional[str] = None, hours: int = 168
    ) -> CachePerformanceAnalysis:
        """Get cache performance analysis."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Base query
            base_query = select(CacheMetadata).where(CacheMetadata.created_at >= cutoff_time)
            
            if data_type:
                base_query = base_query.where(CacheMetadata.data_type == data_type)

            # Get performance metrics by tier - simplified for current schema
            performance_by_tier = [
                {
                    "tier": "default",
                    "avg_hit_rate": 0,  # Not tracked in current schema
                    "avg_access_count": total_accesses / max(1, total_entries),
                    "total_size_bytes": total_size_bytes,
                }
            ]

            # Get hottest cache keys
            hot_keys_query = (
                select(CacheMetadata.cache_key, CacheMetadata.access_count, CacheMetadata.hit_count, CacheMetadata.miss_count)
                .select_from(base_query.subquery())
                .order_by(desc(CacheMetadata.access_count))
                .limit(10)
            )
            hot_keys_result = await self.db.execute(hot_keys_query)
            hottest_keys = [
                {
                    "cache_key": row[0],
                    "access_count": row[1],
                    "hit_rate": (row[2] / (row[2] + row[3]) * 100) if (row[2] + row[3]) > 0 else 0,
                }
                for row in hot_keys_result.fetchall()
            ]

            # Get coldest cache keys (least accessed)
            cold_keys_query = (
                select(CacheMetadata.cache_key, CacheMetadata.access_count, CacheMetadata.last_accessed)
                .select_from(base_query.subquery())
                .order_by(CacheMetadata.access_count)
                .limit(10)
            )
            cold_keys_result = await self.db.execute(cold_keys_query)
            coldest_keys = [
                {
                    "cache_key": row[0],
                    "access_count": row[1],
                    "last_accessed": row[2],
                }
                for row in cold_keys_result.fetchall()
            ]

            # Get inefficient keys - disabled as hit tracking not in current schema
            inefficient_keys = []

            # Generate recommendations
            recommendations = []
            if len(inefficient_keys) > 0:
                recommendations.append("Review cache keys with low hit rates - consider adjusting TTL or eviction policies")
            if len(coldest_keys) > 5:
                recommendations.append("Consider evicting rarely accessed cache entries to free up memory")
            
            # Calculate overall efficiency score
            overall_metrics = await self.get_cache_metrics(hours=hours)
            efficiency_score = min(100, overall_metrics.cache_hit_rate + (overall_metrics.avg_compression_ratio or 0) * 10)

            return CachePerformanceAnalysis(
                data_type=data_type,
                analysis_period_hours=hours,
                efficiency_score=efficiency_score,
                performance_by_tier=performance_by_tier,
                hottest_keys=hottest_keys,
                coldest_keys=coldest_keys,
                inefficient_keys=inefficient_keys,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"Error getting cache performance analysis: {e}")
            raise DatabaseOperationError(f"Failed to get cache performance analysis: {str(e)}", "get_cache_performance_analysis")

    async def get_cache_efficiency_report(
        self, device_id: Optional[UUID] = None, period: str = "last_24h"
    ) -> CacheEfficiencyReport:
        """Generate a cache efficiency report."""
        try:
            # Parse period
            hours_map = {"last_24h": 24, "last_week": 168, "last_month": 720}
            hours = hours_map.get(period, 24)

            # Get overall metrics
            device_ids = [device_id] if device_id else None
            overall_metrics = await self.get_cache_metrics(device_ids=device_ids, hours=hours)

            # Get performance analysis
            performance_analysis = await self.get_cache_performance_analysis(hours=hours)

            # Calculate cache health score
            hit_rate_score = min(100, overall_metrics.cache_hit_rate)
            compression_score = min(100, (overall_metrics.avg_compression_ratio or 1.0) * 50)
            expiration_score = max(0, 100 - (overall_metrics.expired_entries / max(1, overall_metrics.total_entries) * 100))
            
            cache_health_score = (hit_rate_score + compression_score + expiration_score) / 3

            # Generate executive summary
            summary = (
                f"Cache efficiency report for {period}. "
                f"Health score: {cache_health_score:.1f}%. "
                f"Hit rate: {overall_metrics.cache_hit_rate:.1f}%. "
                f"Total entries: {overall_metrics.total_entries}."
            )

            # Generate improvement suggestions
            improvement_suggestions = []
            if overall_metrics.cache_hit_rate < 70:
                improvement_suggestions.append("Increase TTL for frequently accessed data")
            if overall_metrics.expired_entries > overall_metrics.total_entries * 0.2:
                improvement_suggestions.append("Implement automated cleanup of expired entries")
            if not overall_metrics.avg_compression_ratio or overall_metrics.avg_compression_ratio < 2:
                improvement_suggestions.append("Enable compression for large cache entries")

            return CacheEfficiencyReport(
                device_id=device_id,
                report_period=period,
                generated_at=datetime.now(timezone.utc),
                executive_summary=summary,
                cache_health_score=cache_health_score,
                overall_metrics=overall_metrics,
                performance_analysis=performance_analysis,
                improvement_suggestions=improvement_suggestions,
            )

        except Exception as e:
            logger.error(f"Error generating cache efficiency report: {e}")
            raise DatabaseOperationError(f"Failed to generate cache efficiency report: {str(e)}", "generate_cache_efficiency_report")

    async def cleanup_expired_entries(self, dry_run: bool = True) -> int:
        """Clean up expired cache entries."""
        try:
            current_time = datetime.now(timezone.utc)

            # Count expired entries
            count_query = select(func.count()).where(CacheMetadata.expires_at < current_time)
            count_result = await self.db.execute(count_query)
            count_to_delete = count_result.scalar()

            if not dry_run and count_to_delete > 0:
                # Delete expired entries
                from sqlalchemy import delete
                delete_query = delete(CacheMetadata).where(CacheMetadata.expires_at < current_time)
                await self.db.execute(delete_query)
                await self.db.commit()

            return count_to_delete

        except Exception as e:
            logger.error(f"Error cleaning up expired cache entries: {e}")
            raise DatabaseOperationError(f"Failed to cleanup expired cache entries: {str(e)}", "cleanup_expired_entries")

    async def cleanup_old_entries(self, older_than_days: int, dry_run: bool = True) -> int:
        """Clean up old cache metadata entries."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)

            # Count entries to be deleted
            count_query = select(func.count()).where(CacheMetadata.created_at < cutoff_date)
            count_result = await self.db.execute(count_query)
            count_to_delete = count_result.scalar()

            if not dry_run and count_to_delete > 0:
                # Delete old entries
                from sqlalchemy import delete
                delete_query = delete(CacheMetadata).where(CacheMetadata.created_at < cutoff_date)
                await self.db.execute(delete_query)
                await self.db.commit()

            return count_to_delete

        except Exception as e:
            logger.error(f"Error cleaning up old cache entries: {e}")
            raise DatabaseOperationError(f"Failed to cleanup old cache entries: {str(e)}", "cleanup_old_entries")