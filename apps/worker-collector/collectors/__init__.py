"""
采集器模块
"""

from .rss_collector import RSSCollector
from .github_collector import GitHubCollector

__all__ = ["RSSCollector", "GitHubCollector"]