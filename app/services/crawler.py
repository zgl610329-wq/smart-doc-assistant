import asyncio
from typing import Tuple, List
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import NoExtractionStrategy
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("CrawlerService")

# 创建全局信号量，限制并发浏览器数量
crawler_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_CRAWLS)


class CrawlerService:
    @staticmethod
    async def crawl_url(url: str) -> Tuple[str, List[str]]:
        """
        爬取指定URL，返回 (Markdown内容, 链接列表)
        """
        async with crawler_semaphore:  # 限制并发
            logger.info(f"Starting crawl for: {url}")

            try:
                # Crawl4AI 上下文管理器，自动处理浏览器生命周期
                async with AsyncWebCrawler(verbose=True) as crawler:
                    result = await crawler.arun(
                        url=url,
                        # 生产环境通常设为 True，除非你在调试
                        bypass_cache=True,
                        # 开启魔法模式：抗指纹、自动等待加载
                        magic=True,
                        # 策略：不提取结构化 JSON，只要 Markdown
                        extraction_strategy=NoExtractionStrategy(),
                        # 移除外部链接，专注当前文档站
                        exclude_external_links=False,
                    )

                    if not result.success:
                        logger.error(f"Crawl failed for {url}")
                        raise Exception("Failed to crawl page")

                    # 提取链接 (简单清洗)
                    links = []
                    if result.links:
                        # 假设我们优先关注 internal 链接
                        internal = result.links.get("internal", [])
                        links = [link['href'] for link in internal]
                        # 简单去重
                        links = list(set(links))

                    logger.info(f"Successfully crawled {url}, found {len(links)} links")
                    return result.markdown, links

            except Exception as e:
                logger.error(f"Error crawling {url}: {str(e)}")
                raise e