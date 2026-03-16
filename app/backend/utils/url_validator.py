"""
URL验证工具
用于验证和过滤无效的URL
"""

import re
from typing import Optional
from urllib.parse import urlparse


class URLValidator:
    """URL验证器"""
    
    # 图片文件扩展名
    IMAGE_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico',
        '.tiff', '.tif', '.jfif', '.pjpeg', '.pjp'
    }
    
    # 视频文件扩展名
    VIDEO_EXTENSIONS = {
        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v'
    }
    
    # 音频文件扩展名
    AUDIO_EXTENSIONS = {
        '.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac', '.wma'
    }
    
    # 文档文件扩展名
    DOCUMENT_EXTENSIONS = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'
    }
    
    # 压缩文件扩展名
    ARCHIVE_EXTENSIONS = {
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'
    }
    
    # 所有需要过滤的文件扩展名
    FILTERED_EXTENSIONS = (
        IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | 
        DOCUMENT_EXTENSIONS | ARCHIVE_EXTENSIONS
    )
    
    # 图片相关的域名关键词
    IMAGE_DOMAIN_KEYWORDS = [
        'cdn', 'img', 'image', 'pic', 'photo', 'static', 'assets',
        'media', 'upload', 'file', 'storage'
    ]
    
    # 无效的URL模式
    INVALID_URL_PATTERNS = [
        r'^javascript:',
        r'^mailto:',
        r'^tel:',
        r'^#',
        r'^data:',
    ]
    
    @classmethod
    def is_valid_activity_url(cls, url: str) -> bool:
        """
        验证URL是否是有效的活动链接
        
        Args:
            url: 要验证的URL
            
        Returns:
            True如果是有效的活动链接,False否则
        """
        if not url or not isinstance(url, str):
            return False
        
        url = url.strip()
        
        # 检查是否是无效的URL模式
        for pattern in cls.INVALID_URL_PATTERNS:
            if re.match(pattern, url, re.IGNORECASE):
                return False
        
        # 检查是否是文件链接
        if cls.is_file_url(url):
            return False
        
        # 检查是否是图片CDN链接
        if cls.is_image_cdn_url(url):
            return False
        
        # 检查URL是否可解析
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
        except Exception:
            return False
        
        return True
    
    @classmethod
    def is_file_url(cls, url: str) -> bool:
        """
        检查URL是否指向文件
        
        Args:
            url: 要检查的URL
            
        Returns:
            True如果是文件链接,False否则
        """
        url_lower = url.lower()
        
        # 检查文件扩展名
        for ext in cls.FILTERED_EXTENSIONS:
            if url_lower.endswith(ext):
                return True
        
        # 检查URL路径中是否包含文件扩展名
        parsed = urlparse(url_lower)
        path = parsed.path
        
        for ext in cls.FILTERED_EXTENSIONS:
            if ext in path:
                return True
        
        return False
    
    @classmethod
    def is_image_url(cls, url: str) -> bool:
        """
        检查URL是否指向图片
        
        Args:
            url: 要检查的URL
            
        Returns:
            True如果是图片链接,False否则
        """
        url_lower = url.lower()
        
        # 检查图片扩展名
        for ext in cls.IMAGE_EXTENSIONS:
            if url_lower.endswith(ext):
                return True
        
        # 检查URL路径中是否包含图片扩展名
        parsed = urlparse(url_lower)
        path = parsed.path
        
        for ext in cls.IMAGE_EXTENSIONS:
            if ext in path:
                return True
        
        return False
    
    @classmethod
    def is_image_cdn_url(cls, url: str) -> bool:
        """
        检查URL是否是图片CDN链接
        
        Args:
            url: 要检查的URL
            
        Returns:
            True如果是图片CDN链接,False否则
        """
        # 先检查是否是图片URL
        if cls.is_image_url(url):
            return True
        
        url_lower = url.lower()
        
        # 检查域名是否包含图片相关关键词
        parsed = urlparse(url_lower)
        domain = parsed.netloc
        
        for keyword in cls.IMAGE_DOMAIN_KEYWORDS:
            if keyword in domain:
                # 如果域名包含图片关键词,再检查路径
                path = parsed.path
                # 如果路径包含getFile, FileServer等关键词,很可能是文件服务器
                if any(kw in path for kw in ['getfile', 'fileserver', 'download']):
                    return True
        
        return False
    
    @classmethod
    def clean_url(cls, url: str) -> Optional[str]:
        """
        清理URL,移除查询参数和片段
        
        Args:
            url: 要清理的URL
            
        Returns:
            清理后的URL,如果无效返回None
        """
        if not url:
            return None
        
        try:
            parsed = urlparse(url)
            # 重建URL,只保留scheme, netloc和path
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            return clean
        except Exception:
            return None
    
    @classmethod
    def normalize_url(cls, url: str) -> Optional[str]:
        """
        标准化URL
        
        Args:
            url: 要标准化的URL
            
        Returns:
            标准化后的URL,如果无效返回None
        """
        if not url:
            return None
        
        url = url.strip()
        
        # 移除URL末尾的斜杠
        if url.endswith('/'):
            url = url[:-1]
        
        return url
