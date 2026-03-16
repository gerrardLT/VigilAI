"""
VigilAI 错误处理组件
实现统一的错误处理、日志记录和重试机制

Validates: Requirements 12.1, 12.2
"""

import logging
import traceback
from typing import Optional, Callable, Any, Dict
from enum import Enum
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """错误类型枚举"""
    NETWORK = "network"
    PARSING = "parsing"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    UNKNOWN = "unknown"


class ScraperError(Exception):
    """爬虫错误基类"""
    
    def __init__(
        self, 
        message: str, 
        error_type: ErrorType = ErrorType.UNKNOWN,
        source_name: str = "",
        url: str = "",
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.source_name = source_name
        self.url = url
        self.original_error = original_error
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'message': self.message,
            'error_type': self.error_type.value,
            'source_name': self.source_name,
            'url': self.url,
            'timestamp': self.timestamp.isoformat(),
            'original_error': str(self.original_error) if self.original_error else None,
        }


class NetworkError(ScraperError):
    """网络错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_type=ErrorType.NETWORK, **kwargs)


class ParsingError(ScraperError):
    """解析错误"""
    def __init__(self, message: str, html_snippet: str = "", **kwargs):
        super().__init__(message, error_type=ErrorType.PARSING, **kwargs)
        self.html_snippet = html_snippet


class ValidationError(ScraperError):
    """数据验证错误"""
    def __init__(self, message: str, invalid_data: Optional[Dict] = None, **kwargs):
        super().__init__(message, error_type=ErrorType.VALIDATION, **kwargs)
        self.invalid_data = invalid_data


class ErrorHandler:
    """
    统一的错误处理器
    
    功能:
    - 网络错误处理
    - 解析错误处理
    - 验证错误处理
    - 错误日志记录
    - 判断是否可重试
    """
    
    @staticmethod
    def handle_network_error(
        error: Exception, 
        scraper_name: str, 
        url: str
    ) -> bool:
        """
        处理网络错误
        
        Args:
            error: 异常对象
            scraper_name: 爬虫名称
            url: 请求的URL
            
        Returns:
            是否可重试
        """
        error_msg = str(error)
        
        logger.error(
            f"Network error in {scraper_name} for URL {url}: {error_msg}"
        )
        
        # 判断是否可重试
        if isinstance(error, httpx.TimeoutException):
            logger.info(f"Timeout error - retryable")
            return True
        elif isinstance(error, httpx.ConnectError):
            logger.info(f"Connection error - retryable")
            return True
        elif isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            # 5xx错误可重试，4xx错误通常不重试
            if 500 <= status_code < 600:
                logger.info(f"Server error {status_code} - retryable")
                return True
            elif status_code == 429:  # Rate limit
                logger.warning(f"Rate limited - retryable after delay")
                return True
            else:
                logger.info(f"Client error {status_code} - not retryable")
                return False
        elif isinstance(error, (ConnectionError, TimeoutError)):
            return True
        
        return False
    
    @staticmethod
    def handle_parsing_error(
        error: Exception, 
        scraper_name: str, 
        html_snippet: str = ""
    ) -> None:
        """
        处理解析错误
        
        Args:
            error: 异常对象
            scraper_name: 爬虫名称
            html_snippet: HTML片段（用于调试）
        """
        logger.error(f"Parsing error in {scraper_name}: {str(error)}")
        
        if html_snippet:
            # 只记录前500字符，避免日志过大
            snippet = html_snippet[:500] if len(html_snippet) > 500 else html_snippet
            logger.debug(f"HTML snippet: {snippet}")
        
        # 记录堆栈跟踪
        logger.debug(f"Traceback: {traceback.format_exc()}")
    
    @staticmethod
    def handle_validation_error(
        error: Exception, 
        scraper_name: str, 
        data: Optional[Dict] = None
    ) -> None:
        """
        处理数据验证错误
        
        Args:
            error: 异常对象
            scraper_name: 爬虫名称
            data: 无效的数据
        """
        logger.warning(f"Validation error in {scraper_name}: {str(error)}")
        
        if data:
            logger.debug(f"Invalid data: {data}")
    
    @staticmethod
    def log_success(
        scraper_name: str, 
        activity_count: int, 
        elapsed_time: float = 0
    ) -> None:
        """
        记录成功日志
        
        Args:
            scraper_name: 爬虫名称
            activity_count: 抓取的活动数量
            elapsed_time: 耗时（秒）
        """
        if elapsed_time > 0:
            logger.info(
                f"Scraper {scraper_name} completed: "
                f"{activity_count} activities in {elapsed_time:.2f}s"
            )
        else:
            logger.info(
                f"Scraper {scraper_name} completed: {activity_count} activities"
            )
    
    @staticmethod
    def log_error(
        scraper_name: str, 
        error: Exception, 
        context: str = ""
    ) -> None:
        """
        记录错误日志
        
        Args:
            scraper_name: 爬虫名称
            error: 异常对象
            context: 上下文信息
        """
        if context:
            logger.error(f"Error in {scraper_name} ({context}): {str(error)}")
        else:
            logger.error(f"Error in {scraper_name}: {str(error)}")
    
    @staticmethod
    def classify_error(error: Exception) -> ErrorType:
        """
        分类错误类型
        
        Args:
            error: 异常对象
            
        Returns:
            错误类型
        """
        if isinstance(error, (httpx.TimeoutException, TimeoutError)):
            return ErrorType.TIMEOUT
        elif isinstance(error, (httpx.ConnectError, httpx.RequestError, ConnectionError)):
            return ErrorType.NETWORK
        elif isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            if status_code == 429:
                return ErrorType.RATE_LIMIT
            elif status_code in (401, 403):
                return ErrorType.AUTH
            else:
                return ErrorType.NETWORK
        elif isinstance(error, (ValueError, KeyError, AttributeError)):
            return ErrorType.PARSING
        elif isinstance(error, (TypeError,)):
            return ErrorType.VALIDATION
        else:
            return ErrorType.UNKNOWN
    
    @staticmethod
    def is_retryable(error: Exception) -> bool:
        """
        判断错误是否可重试
        
        Args:
            error: 异常对象
            
        Returns:
            是否可重试
        """
        error_type = ErrorHandler.classify_error(error)
        
        retryable_types = {
            ErrorType.NETWORK,
            ErrorType.TIMEOUT,
            ErrorType.RATE_LIMIT,
        }
        
        return error_type in retryable_types
    
    @staticmethod
    def get_retry_delay(error: Exception, attempt: int) -> float:
        """
        获取重试延迟时间（指数退避）
        
        Args:
            error: 异常对象
            attempt: 当前重试次数（从0开始）
            
        Returns:
            延迟时间（秒）
        """
        base_delay = 1.0
        
        error_type = ErrorHandler.classify_error(error)
        
        if error_type == ErrorType.RATE_LIMIT:
            # Rate limit需要更长的延迟
            base_delay = 30.0
        elif error_type == ErrorType.TIMEOUT:
            base_delay = 2.0
        
        # 指数退避
        delay = base_delay * (2 ** attempt)
        
        # 最大延迟60秒
        return min(delay, 60.0)
