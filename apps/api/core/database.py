"""Database configuration with PostGIS support."""
import os
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData, text, event
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
import logging

from core.config import settings

logger = logging.getLogger(__name__)

# Custom naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool if settings.ENVIRONMENT == "test" else None,
    pool_size=settings.DATABASE_POOL_SIZE if settings.ENVIRONMENT != "test" else None,
    max_overflow=settings.DATABASE_MAX_OVERFLOW if settings.ENVIRONMENT != "test" else None,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            # Set RLS context for multi-tenancy
            org_id = getattr(session, "_org_id", None)
            user_id = getattr(session, "_user_id", None)
            
            if org_id:
                await session.execute(
                    text("SET LOCAL app.org_id = :org_id"),
                    {"org_id": str(org_id)}
                )
            if user_id:
                await session.execute(
                    text("SET LOCAL app.user_id = :user_id"),
                    {"user_id": str(user_id)}
                )
            
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database with PostGIS extension."""
    async with engine.begin() as conn:
        # Create PostGIS extension if not exists
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_topology"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS fuzzystrmatch"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
        
        # Create custom types
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE user_role AS ENUM ('owner', 'admin', 'member');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE footprint_type AS ENUM ('main', 'outbuilding', 'driveway');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE cv_artifact_type AS ENUM ('pool', 'tree_canopy', 'driveway');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE export_type AS ENUM ('csv', 'geojson', 'pdf');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE api_provider AS ENUM ('openai', 'anthropic', 'mapbox', 'maptiler', 'google');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        logger.info("Database initialized with PostGIS extensions")


async def create_rls_policies():
    """Create Row Level Security policies for multi-tenancy."""
    async with engine.begin() as conn:
        # Enable RLS on all multi-tenant tables
        tables = [
            'users', 'searches', 'exports', 'audit_logs',
            'user_api_keys', 'derived_buildable', 'cv_artifacts'
        ]
        
        for table in tables:
            await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            
            # Create policies for org isolation
            await conn.execute(text(f"""
                CREATE POLICY {table}_org_isolation ON {table}
                FOR ALL
                USING (org_id = current_setting('app.org_id')::uuid)
                WITH CHECK (org_id = current_setting('app.org_id')::uuid)
            """))
        
        logger.info("Row Level Security policies created")


@asynccontextmanager
async def get_db_context(org_id: Optional[str] = None, user_id: Optional[str] = None):
    """Context manager for database session with RLS context."""
    async with AsyncSessionLocal() as session:
        try:
            if org_id:
                session._org_id = org_id
                await session.execute(
                    text("SET LOCAL app.org_id = :org_id"),
                    {"org_id": org_id}
                )
            if user_id:
                session._user_id = user_id
                await session.execute(
                    text("SET LOCAL app.user_id = :user_id"),
                    {"user_id": user_id}
                )
            
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_health() -> bool:
    """Check if database is healthy and PostGIS is available."""
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT PostGIS_Version()"))
            version = result.scalar()
            logger.info(f"PostGIS version: {version}")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False