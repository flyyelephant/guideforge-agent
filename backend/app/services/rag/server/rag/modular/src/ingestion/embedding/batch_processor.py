"""Batch Processor for orchestrating dense and sparse encoding.

This module implements the Batch Processor component of the Ingestion Pipeline,
responsible for coordinating the encoding workflow and managing batch operations.

Design Principles:
- Orchestration: Coordinates DenseEncoder and SparseEncoder in unified workflow
- Config-Driven: Batch size from settings, not hardcoded
- Observable: Records batch timing and statistics via TraceContext
- Error Handling: Individual batch failures don't crash entire pipeline
- Deterministic: Same inputs produce same batching and results
"""

from typing import List, Dict, Any, Optional, Tuple
import time
from dataclasses import dataclass

from src.core.types import Chunk
from src.ingestion.embedding.dense_encoder import DenseEncoder
from src.ingestion.embedding.sparse_encoder import SparseEncoder


@dataclass
class BatchResult:
    """Result of batch processing operation.批处理 操作结果
    
    Attributes:
        processed_chunks: List of chunks successfully encoded and kept in order
        dense_vectors: List of dense embeddings (one per chunk)密度嵌入列表
        sparse_stats: List of term statistics (one per chunk)稀疏统计列表
        batch_count: Number of batches processed处理的批次数量 
        total_time: Total processing time in seconds 总处理时间（秒）
        successful_chunks: Number of successfully processed chunks 成功处理的块数量
        failed_chunks: Number of chunks that failed processing  处理失败的块数量
    """
    processed_chunks: List[Chunk]
    dense_vectors: List[List[float]]
    sparse_stats: List[Dict[str, Any]]
    batch_count: int
    total_time: float
    successful_chunks: int
    failed_chunks: int


class BatchProcessor:
    """Orchestrates batch processing of chunks through encoding pipeline.
    
    This processor manages the workflow of converting chunks into both dense
    and sparse representations. It divides chunks into batches, drives the
    encoders, and collects timing metrics.
    
    Design:
    - Stateless: No state maintained between process() calls
    - Parallel Encodings: Dense and sparse encoding happen independently
    - Metrics Collection: Records batch-level timing for observability
    - Order Preservation: Output order matches input chunk order
    
    Example:
        >>> from src.libs.embedding.embedding_factory import EmbeddingFactory
        >>> from src.core.settings import load_settings
        >>> 
        >>> settings = load_settings("config/settings.yaml")
        >>> embedding = EmbeddingFactory.create(settings)
        >>> dense_encoder = DenseEncoder(embedding, batch_size=2)
        >>> sparse_encoder = SparseEncoder()
        >>> 
        >>> processor = BatchProcessor(
        ...     dense_encoder=dense_encoder,
        ...     sparse_encoder=sparse_encoder,
        ...     batch_size=2
        ... )
        >>> 
        >>> chunks = [
        ...     Chunk(id="1", text="Hello", metadata={}),
        ...     Chunk(id="2", text="World", metadata={})
        ... ]
        >>> result = processor.process(chunks)
        >>> len(result.dense_vectors) == len(chunks)  # True
        >>> len(result.sparse_stats) == len(chunks)  # True
    """
    
    def __init__(
        self,
        dense_encoder: DenseEncoder,
        sparse_encoder: SparseEncoder,
        batch_size: int = 100,
    ):
        """Initialize BatchProcessor.
        
        Args:
            dense_encoder: DenseEncoder instance for embedding generation
            sparse_encoder: SparseEncoder instance for term statistics
            batch_size: Number of chunks to process per batch (default: 100)
        
        Raises:
            ValueError: If batch_size <= 0
        """
        if batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {batch_size}")
        
        self.dense_encoder = dense_encoder
        self.sparse_encoder = sparse_encoder
        self.batch_size = batch_size
    
    def process(
        self,
        chunks: List[Chunk],
        trace: Optional[Any] = None,
    ) -> BatchResult:
        """Process chunks through dense and sparse encoding pipeline.
        
        Workflow:
        1. Validate inputs
        2. Create batches from chunks
        3. Process each batch through both encoders
        4. Collect results and timing metrics
        5. Record to TraceContext if provided
        
        Args:
            chunks: List of Chunk objects to process
            trace: Optional TraceContext for observability
        
        Returns:
            BatchResult containing vectors, statistics, and metrics
        
        Raises:
            ValueError: If chunks list is empty
            RuntimeError: If both encoders fail completely
        
        Example:
            >>> chunks = [Chunk(id=f"{i}", text=f"Text {i}", metadata={}) 
            ...           for i in range(5)]
            >>> result = processor.process(chunks)
            >>> result.batch_count  # 3 (with batch_size=2)
            >>> result.successful_chunks  # 5
        """
        if not chunks:
            raise ValueError("Cannot process empty chunks list") #处理空块列表时引发错误
        
        start_time = time.time()
        
        # Create batches
        batches = self._create_batches(chunks) #将块划分为批次 _create_batches方法：依靠步长切chunks列表
        batch_count = len(batches)
        
        # Process all batches
        processed_chunks: List[Chunk] = []
        dense_vectors: List[List[float]] = []   #初始化结果容器
        sparse_stats: List[Dict[str, Any]] = []
        successful_chunks = 0
        failed_chunks = 0
        
        for batch_idx, batch in enumerate(batches): #遍历批次，batch_idx为批次索引，batch为当前批次的块列表
            batch_start = time.time()
            
            try:
                (
                    batch_chunks,
                    batch_dense,
                    batch_sparse,
                    batch_successes,
                    batch_failures,
                ) = self._process_batch_recursive(batch, trace=trace, batch_label=str(batch_idx))
                processed_chunks.extend(batch_chunks)
                dense_vectors.extend(batch_dense)
                sparse_stats.extend(batch_sparse)
                successful_chunks += batch_successes
                failed_chunks += batch_failures
                
            except Exception as e:
                # Record failure but continue with remaining batches
                failed_chunks += len(batch)
                if trace:
                    trace.record_stage(
                        f"batch_{batch_idx}_error",
                        {"error": str(e), "batch_size": len(batch)}
                    )
            
            batch_duration = time.time() - batch_start
            
            # Record batch timing if trace available
            if trace:
                trace.record_stage(
                    f"batch_{batch_idx}",
                    {
                        "batch_size": len(batch),
                        "duration_seconds": batch_duration,
                        "chunks_processed": len(batch)
                    }
                )
        
        total_time = time.time() - start_time
        
        # Record overall processing statistics
        if trace:
            trace.record_stage(
                "batch_processing",
                {
                    "total_chunks": len(chunks),
                    "batch_count": batch_count,
                    "batch_size": self.batch_size,
                    "successful_chunks": successful_chunks,
                    "failed_chunks": failed_chunks,
                    "total_time_seconds": total_time
                }
            )
        
        return BatchResult(
            processed_chunks=processed_chunks,
            dense_vectors=dense_vectors,
            sparse_stats=sparse_stats,
            batch_count=batch_count,
            total_time=total_time,
            successful_chunks=successful_chunks,
            failed_chunks=failed_chunks
        )

    def _process_batch_recursive(
        self,
        batch: List[Chunk],
        trace: Optional[Any] = None,
        batch_label: str = "",
    ) -> Tuple[List[Chunk], List[List[float]], List[Dict[str, Any]], int, int]:
        """Process a batch and split it recursively when either encoder fails."""
        try:
            batch_dense = self.dense_encoder.encode(batch, trace=trace)
            batch_sparse = self.sparse_encoder.encode(batch, trace=trace)
            if len(batch_dense) != len(batch) or len(batch_sparse) != len(batch):
                raise RuntimeError(
                    f"Encoder output mismatch for batch {batch_label or 'root'}: "
                    f"chunks={len(batch)} dense={len(batch_dense)} sparse={len(batch_sparse)}"
                )
            return batch, batch_dense, batch_sparse, len(batch), 0
        except Exception as exc:
            if len(batch) == 1:
                if trace:
                    trace.record_stage(
                        f"batch_{batch_label or 'root'}_single_error",
                        {
                            "error": str(exc),
                            "chunk_id": batch[0].id,
                            "source_path": batch[0].metadata.get("source_path", ""),
                            "chunk_index": batch[0].metadata.get("chunk_index", -1),
                        },
                    )
                return [], [], [], 0, 1

            split_at = max(1, len(batch) // 2)
            # Some providers partially fail on larger batches. Split until the
            # smallest failing chunk is isolated so the rest of the document can
            # still be indexed instead of losing the whole file.
            left_result = self._process_batch_recursive(
                batch[:split_at],
                trace=trace,
                batch_label=f"{batch_label}L",
            )
            right_result = self._process_batch_recursive(
                batch[split_at:],
                trace=trace,
                batch_label=f"{batch_label}R",
            )
            return (
                left_result[0] + right_result[0],
                left_result[1] + right_result[1],
                left_result[2] + right_result[2],
                left_result[3] + right_result[3],
                left_result[4] + right_result[4],
            )
    
    def _create_batches(self, chunks: List[Chunk]) -> List[List[Chunk]]:
        """Divide chunks into batches of specified size.
        
        Args:
            chunks: List of chunks to batch
        
        Returns:
            List of batches, where each batch is a list of chunks.
            Order is preserved: first batch contains chunks[0:batch_size],
            second batch contains chunks[batch_size:2*batch_size], etc.
        
        Example:
            >>> chunks = [Chunk(id=f"{i}", text="", metadata={}) for i in range(5)]
            >>> batches = processor._create_batches(chunks)
            >>> len(batches)  # 3 (with batch_size=2)
            >>> [len(b) for b in batches]  # [2, 2, 1]
        """
        batches = []
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]      #若batch_size=2，则两个chunks为一批，最后一批可能不足batch_size
            batches.append(batch)
        return batches
    
    def get_batch_count(self, total_chunks: int) -> int:
        """Calculate number of batches for given chunk count.
        
        Utility method for planning and testing.
        
        Args:
            total_chunks: Total number of chunks to process
        
        Returns:
            Number of batches that will be created
        
        Example:
            >>> processor.get_batch_count(5)  # 3 (with batch_size=2)
            >>> processor.get_batch_count(4)  # 2
            >>> processor.get_batch_count(0)  # 0
        """
        if total_chunks <= 0:
            return 0
        return (total_chunks + self.batch_size - 1) // self.batch_size
