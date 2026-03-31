"""
采集器模块
"""

from .rss_collector import RSSCollector
from .github_collector import GitHubCollector
from .x_collector import XCollector
from .web_collector import WebCollector

__all__ = ["RSSCollector", "GitHubCollector", "XCollector", "WebCollector"]
