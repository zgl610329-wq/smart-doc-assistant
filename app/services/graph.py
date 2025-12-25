from typing import TypedDict, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from app.core.config import settings
from app.services.crawler import CrawlerService
from app.core.logger import get_logger

logger = get_logger("GraphService")


# 1. 定义状态
class WorkflowState(TypedDict):
    url: str
    raw_markdown: str
    links: List[str]
    final_output: str
    error: str


# 2. 定义节点

async def crawl_node(state: WorkflowState):
    """节点：调用 Crawl4AI 获取内容"""
    try:
        markdown, links = await CrawlerService.crawl_url(state["url"])
        return {
            "raw_markdown": markdown,
            "links": links[:20],  # 限制返回链接数量，防止 Payload 过大
            "error": None
        }
    except Exception as e:
        return {"error": str(e), "raw_markdown": "", "links": []}


async def process_node(state: WorkflowState):
    """节点：调用 LLM 进行翻译、注释和绘图"""
    if state.get("error"):
        return {"final_output": f"Error during crawling: {state['error']}"}

    if not state.get("raw_markdown"):
        return {"final_output": "Error during crawling.", "error": "raw_markdown is empty"}

    logger.info("Processing content with LLM...")

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.1,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=settings.DASHSCOPE_API_KEY
    )

    system_prompt = """
    你是一个高级技术文档助手。请处理用户提供的 Markdown 源码：

    1. **翻译**: 将所有说明性文本翻译成流畅、专业的技术中文。
    2. **代码注释**: 保持代码块原样（不要翻译变量名），但**必须**在每一行关键代码后添加中文注释（格式：`# <注释>` 或 `// <注释>`）。
    3. **Mermaid 可视化**: 如果文中包含架构描述、流程逻辑或 img 标签引用了流程图，请在 Markdown 中生成 `mermaid` 代码块重绘该图。
    4. **清洗**: 移除无用的页眉、页脚导航文本，只保留正文。
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Markdown Content:\n\n{content}")
    ])

    chain = prompt | llm | StrOutputParser()

    # 安全截断：防止超长文档导致 Token 溢出 (生产环境建议使用 Splitter 分块处理)
    # 假设 GPT-4o 上下文很大，但为了响应速度，截取前 20k 字符通常包含核心内容
    safe_content = state["raw_markdown"][:20000]

    try:
        result = await chain.ainvoke({"content": safe_content})
        return {"final_output": result}
    except Exception as e:
        logger.error(f"LLM processing error: {e}")
        return {"final_output": "Error processing content with LLM.", "error": str(e)}


# 3. 构建图
workflow = StateGraph(WorkflowState)

workflow.add_node("crawler", crawl_node)
workflow.add_node("processor", process_node)

workflow.set_entry_point("crawler")
workflow.add_edge("crawler", "processor")
workflow.add_edge("processor", END)

# 编译图应用
app_graph = workflow.compile()


async def run_workflow(url: str):
    """对外暴露的运行函数"""
    initial_state = {
        "url": url,
        "raw_markdown": "",
        "links": [],
        "final_output": "",
        "error": None
    }
    result = await app_graph.ainvoke(initial_state)
    return result