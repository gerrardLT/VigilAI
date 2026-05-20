"""SQLite connection pool with WAL mode and configurable size.

Provides async connection pooling for SQLite databases using aiosqlite.
Enables concurrent read access via WAL journal mode and manages connection
lifecycle with configurable pool size and idle timeout.
"""

import asyncio
from contextlib import asynccontextmanager

import aiosqlite


class SQLitePool:
    """Async SQLite connection pool with WAL mode support.

    Manages a pool of aiosqlite connections with configurable maximum size.
    Connections are reused from the pool when available, or created on demand
    up to max_size. When the pool is exhausted, callers wait up to 30 seconds
    for a connection to be returned.

    Attributes:
        db_path: Path to the SQLite database file.
        max_size: Maximum number of concurrent connections.
        idle_timeout: Seconds before idle connections are closed (reserved for future use).
    """

    def __init__(self, db_path: str, max_size: int = 5, idle_timeout: int = 300):
        """Initialize the connection pool.

        Args:
            db_path: Path to the SQLite database file.
            max_size: Maximum number of connections in the pool. Defaults to 5.
            idle_timeout: Seconds before idle connections are eligible for cleanup.
                Defaults to 300 (5 minutes).
        """
        self.db_path = db_path
        self.max_size = max_size
        self.idle_timeout = idle_timeout
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._size = 0
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Enable WAL mode and set performance pragmas on first connection.

        This should be called once after creating the pool to configure the
        database for concurrent access. Sets:
        - journal_mode=WAL for concurrent readers
        - busy_timeout=5000 to wait on locks instead of failing immediately
        - synchronous=NORMAL for better write performance with acceptable durability
        """
        async with self.acquire() as conn:
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA busy_timeout=5000")
            await conn.execute("PRAGMA synchronous=NORMAL")

    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool.

        Yields an aiosqlite connection that is automatically returned to the
        pool when the context manager exits. If the pool is empty and max_size
        has not been reached, a new connection is created. If max_size is
        reached, waits up to 30 seconds for a connection to become available.

        Yields:
            An aiosqlite.Connection instance with row_factory set to aiosqlite.Row.

        Raises:
            asyncio.TimeoutError: If no connection becomes available within 30 seconds.
        """
        conn = await self._get_connection()
        try:
            yield conn
        finally:
            await self._return_connection(conn)

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get a connection from the pool or create a new one.

        Attempts to get an idle connection from the pool. If none available
        and pool size is below max_size, creates a new connection. Otherwise
        waits up to 30 seconds for a connection to be returned.

        Returns:
            An aiosqlite.Connection instance.

        Raises:
            asyncio.TimeoutError: If no connection becomes available within 30 seconds.
        """
        # Try to get an existing idle connection first
        try:
            return self._pool.get_nowait()
        except asyncio.QueueEmpty:
            pass

        # Try to create a new connection if under max_size
        async with self._lock:
            if self._size < self.max_size:
                self._size += 1
                conn = await aiosqlite.connect(self.db_path)
                conn.row_factory = aiosqlite.Row
                return conn

        # Pool is full, wait for a connection to be returned
        return await asyncio.wait_for(self._pool.get(), timeout=30.0)

    async def _return_connection(self, conn: aiosqlite.Connection):
        """Return a connection to the pool or close it if pool is full.

        Args:
            conn: The connection to return.
        """
        try:
            self._pool.put_nowait(conn)
        except asyncio.QueueFull:
            await conn.close()
            async with self._lock:
                self._size -= 1

    async def close_all(self):
        """Close all pooled connections and reset pool state.

        Should be called during application shutdown to cleanly release
        all database connections.
        """
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                await conn.close()
            except asyncio.QueueEmpty:
                break
        async with self._lock:
            self._size = 0
