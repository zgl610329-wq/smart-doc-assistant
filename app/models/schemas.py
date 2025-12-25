from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional


class DocProcessRequest(BaseModel):
    url: HttpUrl = Field(..., description="需要处理的目标网页URL")
    # 新增 download 参数，默认为 False
    download: bool = Field(default=False, description="是否直接下载为Markdown文件")


class DocProcessResponse(BaseModel):
    url: str
    processed_markdown: str = Field(..., description="处理后的Markdown内容")
    discovered_links: List[str] = Field(default=[], description="页面内发现的同域链接")
    status: str = "success"
    error: Optional[str] = None