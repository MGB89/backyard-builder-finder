"""
Export service using configurable storage provider.
Supports both Supabase Storage and AWS S3 depending on configuration.
"""

import json
import csv
import io
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, BinaryIO
from pathlib import Path
from enum import Enum

from core.config import settings
from services.providers import get_storage_provider, get_metrics_provider
from services.background_jobs import get_background_job_service, JobType

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""
    CSV = "csv"
    GEOJSON = "geojson"
    PDF = "pdf"
    XLSX = "xlsx"


class ExportService:
    """Service for generating and managing file exports with configurable storage."""
    
    def __init__(self):
        self._storage_provider = None
        self._metrics_provider = None
        
        logger.info(f"ExportService initialized with storage provider: {settings.STORAGE_PROVIDER}")
    
    @property
    def storage_provider(self):
        """Get the storage provider instance."""
        if self._storage_provider is None:
            try:
                self._storage_provider = get_storage_provider()
            except Exception as e:
                logger.error(f"Failed to initialize storage provider: {e}")
                self._storage_provider = None
        return self._storage_provider
    
    @property
    def metrics_provider(self):
        """Get the metrics provider instance."""
        if self._metrics_provider is None:
            try:
                self._metrics_provider = get_metrics_provider()
            except Exception as e:
                logger.warning(f"Failed to initialize metrics provider: {e}")
                self._metrics_provider = None
        return self._metrics_provider
    
    async def create_export(
        self,
        export_id: str,
        user_id: str,
        org_id: str,
        search_id: str,
        format: ExportFormat,
        data: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an export file and store it using the configured provider.
        
        Args:
            export_id: Unique export identifier
            user_id: User ID
            org_id: Organization ID
            search_id: Search ID this export is based on
            format: Export format
            data: Data to export
            metadata: Optional metadata to include
            
        Returns:
            Dictionary with export details including file path and signed URL
        """
        if not self.storage_provider:
            raise RuntimeError("Storage provider not available")
        
        try:
            logger.info(f"Creating {format.value} export {export_id} for user {user_id}")
            
            # Generate file content
            file_content = await self._generate_file_content(format, data, metadata)
            file_size = len(file_content)
            
            # Generate storage key
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_key = f"exports/{org_id}/{user_id}/{timestamp}_{export_id}.{format.value}"
            
            # Upload to storage
            await self.storage_provider.put_object(
                key=file_key,
                data=file_content,
                options={
                    "content_type": self._get_content_type(format),
                    "metadata": {
                        "export_id": export_id,
                        "user_id": user_id,
                        "org_id": org_id,
                        "search_id": search_id,
                        "created_at": datetime.utcnow().isoformat()
                    }
                }
            )
            
            # Generate signed URL for download
            signed_url = await self.storage_provider.get_signed_url(
                key=file_key,
                options={
                    "expires_in": 3600,  # 1 hour
                    "response_content_disposition": f"attachment; filename={export_id}.{format.value}"
                }
            )
            
            # Record metrics
            if self.metrics_provider:
                try:
                    await self.metrics_provider.increment_counter(
                        "exports_created_total",
                        tags={"format": format.value, "org_id": org_id}
                    )
                    await self.metrics_provider.record_histogram(
                        "export_file_size_bytes",
                        file_size,
                        tags={"format": format.value}
                    )
                except Exception as e:
                    logger.warning(f"Failed to record export metrics: {e}")
            
            result = {
                "export_id": export_id,
                "file_path": file_key,
                "file_size_bytes": file_size,
                "signed_url": signed_url,
                "signed_url_expires": datetime.utcnow() + timedelta(hours=1),
                "format": format.value,
                "created_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Export {export_id} created successfully: {file_size} bytes")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create export {export_id}: {e}")
            
            # Record failure metrics
            if self.metrics_provider:
                try:
                    await self.metrics_provider.increment_counter(
                        "exports_failed_total",
                        tags={"format": format.value, "org_id": org_id, "error": "creation_failed"}
                    )
                except Exception as metric_error:
                    logger.warning(f"Failed to record failure metrics: {metric_error}")
            
            raise
    
    async def get_signed_url(
        self,
        file_path: str,
        expires_in: int = 3600,
        filename: Optional[str] = None
    ) -> str:
        """
        Get a signed URL for downloading an export file.
        
        Args:
            file_path: Storage key for the file
            expires_in: URL expiration time in seconds
            filename: Optional filename for download
            
        Returns:
            Signed URL for file download
        """
        if not self.storage_provider:
            raise RuntimeError("Storage provider not available")
        
        options = {"expires_in": expires_in}
        if filename:
            options["response_content_disposition"] = f"attachment; filename={filename}"
        
        return await self.storage_provider.get_signed_url(file_path, options)
    
    async def delete_export(self, file_path: str) -> bool:
        """
        Delete an export file from storage.
        
        Args:
            file_path: Storage key for the file to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.storage_provider:
            raise RuntimeError("Storage provider not available")
        
        try:
            await self.storage_provider.delete(file_path)
            logger.info(f"Deleted export file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete export file {file_path}: {e}")
            return False
    
    async def cleanup_expired_exports(self, retention_days: int = 7) -> int:
        """
        Clean up expired export files.
        
        Args:
            retention_days: Number of days to retain exports
            
        Returns:
            Number of files cleaned up
        """
        # This would typically query the database for expired exports
        # and delete them from storage. For now, just log the intent.
        logger.info(f"Cleanup expired exports older than {retention_days} days")
        return 0
    
    async def _generate_file_content(
        self,
        format: ExportFormat,
        data: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate file content based on format."""
        if format == ExportFormat.CSV:
            return await self._generate_csv(data, metadata)
        elif format == ExportFormat.GEOJSON:
            return await self._generate_geojson(data, metadata)
        elif format == ExportFormat.PDF:
            return await self._generate_pdf(data, metadata)
        elif format == ExportFormat.XLSX:
            return await self._generate_xlsx(data, metadata)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def _generate_csv(
        self,
        data: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate CSV file content."""
        if not data:
            return b""
        
        output = io.StringIO()
        
        # Add metadata as comments if provided
        if metadata:
            output.write(f"# Export generated at: {datetime.utcnow().isoformat()}\n")
            for key, value in metadata.items():
                output.write(f"# {key}: {value}\n")
            output.write("\n")
        
        # Write CSV data
        fieldnames = data[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in data:
            # Flatten nested objects to JSON strings
            flattened_row = {}
            for key, value in row.items():
                if isinstance(value, (dict, list)):
                    flattened_row[key] = json.dumps(value)
                else:
                    flattened_row[key] = value
            writer.writerow(flattened_row)
        
        return output.getvalue().encode('utf-8')
    
    async def _generate_geojson(
        self,
        data: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate GeoJSON file content."""
        features = []
        
        for item in data:
            # Extract geometry and properties
            geometry = item.get('geometry')
            properties = {k: v for k, v in item.items() if k != 'geometry'}
            
            if geometry:
                feature = {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": properties
                }
                features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # Add metadata
        if metadata:
            geojson["metadata"] = metadata
        
        return json.dumps(geojson, indent=2).encode('utf-8')
    
    async def _generate_pdf(
        self,
        data: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate PDF file content."""
        # For now, return a placeholder PDF content
        # In production, you'd use a library like reportlab
        content = f"PDF Export Generated at {datetime.utcnow().isoformat()}\n"
        content += f"Records: {len(data)}\n"
        if metadata:
            content += f"Metadata: {json.dumps(metadata, indent=2)}\n"
        
        return content.encode('utf-8')
    
    async def _generate_xlsx(
        self,
        data: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate Excel file content."""
        # For now, return CSV content
        # In production, you'd use a library like openpyxl
        return await self._generate_csv(data, metadata)
    
    def _get_content_type(self, format: ExportFormat) -> str:
        """Get content type for export format."""
        content_types = {
            ExportFormat.CSV: "text/csv",
            ExportFormat.GEOJSON: "application/geo+json",
            ExportFormat.PDF: "application/pdf",
            ExportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        return content_types.get(format, "application/octet-stream")


# Global service instance
_export_service = ExportService()


def get_export_service() -> ExportService:
    """Get the global export service instance."""
    return _export_service


# Background job handler for export generation
async def export_generation_handler(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Background job handler for export generation."""
    try:
        payload = job_data.get("payload", {})
        export_id = payload.get("export_id")
        user_id = payload.get("user_id")
        org_id = payload.get("org_id")
        search_id = payload.get("search_id")
        format_str = payload.get("format")
        data = payload.get("data", [])
        metadata = payload.get("metadata")
        
        if not all([export_id, user_id, org_id, search_id, format_str]):
            raise ValueError("Missing required export parameters")
        
        export_format = ExportFormat(format_str)
        export_service = get_export_service()
        
        result = await export_service.create_export(
            export_id=export_id,
            user_id=user_id,
            org_id=org_id,
            search_id=search_id,
            format=export_format,
            data=data,
            metadata=metadata
        )
        
        return {
            "status": "completed",
            "export_details": result
        }
        
    except Exception as e:
        logger.error(f"Export generation job failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


# Register the export handler
def register_export_handler():
    """Register the export generation handler."""
    job_service = get_background_job_service()
    job_service.register_handler(JobType.EXPORT_GENERATION, export_generation_handler)


# Initialize export handler
register_export_handler()