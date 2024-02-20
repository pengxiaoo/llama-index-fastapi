from typing import Any
from llama_index.core.tools import QueryEngineTool
from llama_index.core.tools.types import ToolOutput

DEFAULT_NAME = "my_query_engine_tool"
DEFAULT_DESCRIPTION = """The only difference between MyQueryEngineTool and QueryEngineTool is: 
MyQueryEngineTool utilizes source_nodes while QueryEngineTool doesn't
"""
MATCHED_MARK = "Matched:"


def get_matched_question(response):
    response_str = str(response)
    if not response_str or response_str == "None" or response_str == "":
        source_nodes = response.source_nodes
        if len(source_nodes) > 0:
            matched_node = source_nodes[0]
            matched_question = matched_node.text
            return f"{MATCHED_MARK}{matched_question}"
    else:
        return str(response)


class MyQueryEngineTool(QueryEngineTool):

    def call(self, *args: Any, **kwargs: Any) -> ToolOutput:
        tool_output = super().call(*args, **kwargs)
        matched_question = get_matched_question(tool_output.raw_output)
        tool_output.content = matched_question
        return tool_output

    async def acall(self, *args: Any, **kwargs: Any) -> ToolOutput:
        tool_output = super().call(*args, **kwargs)
        matched_question = get_matched_question(tool_output.raw_output)
        tool_output.content = matched_question
        return tool_output
