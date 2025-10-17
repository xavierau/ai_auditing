"""Secure KB Retriever - adds access control and audit logging to KB retrieval.

Extends KBRetriever with:
- Access level enforcement (PUBLIC, TENANT, RESTRICTED)
- User role-based access control
- Comprehensive audit logging for all operations
"""

import time
from typing import List, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from genreport.core.database.models import User, KnowledgeBase, KBChunk
from genreport.core.retrieval.kb_retriever import KBRetriever
from genreport.core.security.audit_logger import AuditLogger


class SecureKBRetriever:
    """KB retriever with access control and audit logging.

    Wraps KBRetriever to add:
    - Access level filtering (PUBLIC, TENANT, RESTRICTED)
    - Role-based access control (admin vs viewer)
    - Comprehensive audit logging

    Access Rules:
    - PUBLIC: Accessible to all users in the jurisdiction
    - TENANT: Accessible only to users in the owning tenant
    - RESTRICTED: Accessible only to admins in the owning tenant

    Example:
        >>> retriever = SecureKBRetriever(
        ...     db=db,
        ...     jurisdiction="HK",
        ...     tenant_id=tenant_id,
        ...     user_id=user_id
        ... )
        >>> results = retriever.retrieve("revenue recognition", top_k=5)
    """

    def __init__(
        self,
        db: Session,
        jurisdiction: str,
        tenant_id: UUID,
        user_id: int,
    ):
        """Initialize secure KB retriever.

        Args:
            db: Database session
            jurisdiction: Jurisdiction code (HK, SG, AU)
            tenant_id: Tenant UUID for access control
            user_id: User ID for audit logging and role checking
        """
        self.db = db
        self.jurisdiction = jurisdiction
        self.tenant_id = tenant_id
        self.user_id = user_id

        # Initialize base retriever
        self.base_retriever = KBRetriever(
            db=db,
            jurisdiction=jurisdiction,
            tenant_id=tenant_id,
        )

        # Get user for role checking
        self.user = self._get_user()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        chunk_types: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Retrieve relevant chunks with access control and audit logging.

        Args:
            query: Search query text
            top_k: Maximum number of results to return
            chunk_types: Optional filter by chunk types

        Returns:
            List of accessible chunks with metadata

        Raises:
            ValueError: If query is empty
        """
        start_time = time.time()

        try:
            # Step 1: Perform base retrieval
            results = self.base_retriever.retrieve(
                query=query,
                top_k=top_k * 2,  # Get more initially to account for filtering
                chunk_types=chunk_types,
            )

            # Step 2: Apply access control filtering
            accessible_results = self._filter_by_access_control(results)

            # Step 3: Limit to requested top_k
            accessible_results = accessible_results[:top_k]

            # Step 4: Log successful retrieval
            response_time_ms = (time.time() - start_time) * 1000
            self._log_retrieval_success(query, accessible_results, response_time_ms)

            return accessible_results

        except Exception as e:
            # Log failed retrieval
            self._log_retrieval_failure(query, str(e))
            raise

    def retrieve_by_standard(
        self,
        standard: str,
        query: str,
        top_k: int = 5,
    ) -> List[Dict]:
        """Retrieve chunks from a specific standard with access control.

        Args:
            standard: Standard code (e.g., 'HKFRS 15', 'SME-FRS')
            query: Search query text
            top_k: Maximum number of results

        Returns:
            List of accessible chunks from the specified standard
        """
        start_time = time.time()

        try:
            # Perform base retrieval
            results = self.base_retriever.retrieve_by_standard(
                standard=standard,
                query=query,
                top_k=top_k * 2,  # Get more initially
            )

            # Apply access control
            accessible_results = self._filter_by_access_control(results)
            accessible_results = accessible_results[:top_k]

            # Log success
            response_time_ms = (time.time() - start_time) * 1000
            self._log_retrieval_success(
                query, accessible_results, response_time_ms, standard=standard
            )

            return accessible_results

        except Exception as e:
            self._log_retrieval_failure(query, str(e), standard=standard)
            raise

    def get_chunk_by_id(self, chunk_id: int) -> Optional[Dict]:
        """Get a specific chunk by ID with access control.

        Args:
            chunk_id: Chunk ID to retrieve

        Returns:
            Chunk data dict or None if not found or not accessible
        """
        try:
            # Get chunk using base retriever
            chunk_data = self.base_retriever.get_chunk_by_id(chunk_id)

            if not chunk_data:
                return None

            # Check access control
            if not self._can_access_chunk(chunk_id):
                # Log access denial
                AuditLogger.log_event(
                    db=self.db,
                    event_type="KB_ACCESS_DENIED",
                    action="READ",
                    user_id=self.user_id,
                    tenant_id=self.tenant_id,
                    resource_type="kb_chunk",
                    resource_id=chunk_id,
                    details={
                        "reason": "Insufficient permissions",
                        "jurisdiction": self.jurisdiction,
                    },
                    status="DENIED",
                )
                return None

            # Log successful access
            AuditLogger.log_event(
                db=self.db,
                event_type="KB_CHUNK_ACCESS",
                action="READ",
                user_id=self.user_id,
                tenant_id=self.tenant_id,
                resource_type="kb_chunk",
                resource_id=chunk_id,
                details={
                    "jurisdiction": self.jurisdiction,
                    "document_id": chunk_data["kb_document_id"],
                },
                status="SUCCESS",
            )

            return chunk_data

        except Exception as e:
            AuditLogger.log_event(
                db=self.db,
                event_type="KB_CHUNK_ACCESS",
                action="READ",
                user_id=self.user_id,
                tenant_id=self.tenant_id,
                resource_type="kb_chunk",
                resource_id=chunk_id,
                details={"error": str(e)},
                status="FAILURE",
            )
            raise

    def _filter_by_access_control(self, results: List[Dict]) -> List[Dict]:
        """Filter results by access control rules.

        Args:
            results: List of chunks from base retrieval

        Returns:
            Filtered list of accessible chunks
        """
        accessible_results = []

        for result in results:
            chunk_id = result["chunk_id"]

            if self._can_access_chunk(chunk_id):
                accessible_results.append(result)

        return accessible_results

    def _can_access_chunk(self, chunk_id: int) -> bool:
        """Check if user can access a specific chunk.

        Args:
            chunk_id: Chunk ID to check

        Returns:
            True if accessible, False otherwise
        """
        # Get chunk and KB document
        chunk_result = (
            self.db.query(KBChunk, KnowledgeBase)
            .join(KnowledgeBase, KBChunk.kb_document_id == KnowledgeBase.id)
            .filter(KBChunk.id == chunk_id)
            .first()
        )

        if not chunk_result:
            return False

        chunk, kb_doc = chunk_result

        # PUBLIC documents are accessible to all
        if kb_doc.tenant_id is None and kb_doc.access_level == "PUBLIC":
            return True

        # Must be same tenant for TENANT and RESTRICTED
        if kb_doc.tenant_id != self.tenant_id:
            return False

        # TENANT level - accessible to all users in tenant
        if kb_doc.access_level == "TENANT":
            return True

        # RESTRICTED level - only accessible to admins
        if kb_doc.access_level == "RESTRICTED":
            return self.user.role == "admin"

        # Default deny
        return False

    def _get_user(self) -> User:
        """Get user record for role checking.

        Returns:
            User record

        Raises:
            ValueError: If user not found
        """
        user = self.db.query(User).filter(User.id == self.user_id).first()

        if not user:
            raise ValueError(f"User not found: {self.user_id}")

        return user

    def _log_retrieval_success(
        self,
        query: str,
        results: List[Dict],
        response_time_ms: float,
        standard: Optional[str] = None,
    ):
        """Log successful retrieval to audit log.

        Args:
            query: Search query
            results: Retrieved results
            response_time_ms: Response time in milliseconds
            standard: Optional standard filter
        """
        details = {
            "query": query,
            "jurisdiction": self.jurisdiction,
            "results_count": len(results),
            "response_time_ms": response_time_ms,
        }

        if standard:
            details["standard"] = standard

        AuditLogger.log_event(
            db=self.db,
            event_type="KB_RETRIEVAL",
            action="READ",
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            resource_type="knowledge_base",
            details=details,
            status="SUCCESS",
        )

    def _log_retrieval_failure(
        self,
        query: str,
        error: str,
        standard: Optional[str] = None,
    ):
        """Log failed retrieval to audit log.

        Args:
            query: Search query
            error: Error message
            standard: Optional standard filter
        """
        details = {
            "query": query,
            "jurisdiction": self.jurisdiction,
            "error": error,
        }

        if standard:
            details["standard"] = standard

        AuditLogger.log_event(
            db=self.db,
            event_type="KB_RETRIEVAL",
            action="READ",
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            resource_type="knowledge_base",
            details=details,
            status="FAILURE",
        )
