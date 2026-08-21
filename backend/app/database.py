"""CognoDB connection pool using the official Neo4j driver."""

import logging
from contextlib import contextmanager
from typing import Any, Generator, Optional

from neo4j import Driver, GraphDatabase, Session
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from app.config import settings

logger = logging.getLogger(__name__)

_driver: Optional[Driver] = None


def get_driver() -> Driver:
    """Return a singleton driver with connection pooling."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.cogno_uri,
            auth=(settings.cogno_user, settings.cogno_password),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_acquisition_timeout=60,
        )
    return _driver


def verify_connection() -> bool:
    """Verify CognoDB connectivity at startup."""
    try:
        driver = get_driver()
        driver.verify_connectivity()
        logger.info("CognoDB connection verified")
        return True
    except (ServiceUnavailable, Neo4jError) as exc:
        logger.error("CognoDB connection failed: %s", exc)
        return False


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for a database session."""
    driver = get_driver()
    session = driver.session()
    try:
        yield session
    finally:
        session.close()


def run_query(
    cypher: str,
    parameters: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Execute a parameterized Cypher query and return records as dicts."""
    params = parameters or {}
    with get_session() as session:
        result = session.run(cypher, params)
        return [record.data() for record in result]


def run_write(cypher: str, parameters: Optional[dict[str, Any]] = None) -> None:
    """Execute a write query inside an explicit transaction."""
    params = parameters or {}
    with get_session() as session:
        session.execute_write(lambda tx: tx.run(cypher, params))


def close_driver() -> None:
    """Close the driver pool on shutdown."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
        logger.info("CognoDB driver closed")
