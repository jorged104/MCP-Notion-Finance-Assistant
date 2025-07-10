from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agents.schemas import State
from agents.user_info import user_info_node
from agents.ocr_agent import ocr_node
from agents.finance_experts import make_finance_expert_node
from agents.rate_limited_tool_node import build_rate_limited_tool_node
from agents.router_node import router_node
from agents.finance_qa_node import make_finance_qa_node
from agents.finance_classifier_node import make_finance_classifier_node, finance_phase_condition
from langgraph.prebuilt import tools_condition

def build_graph(config, tools, resource_names):
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=config["llm"]["api_key"])
    llm_complex = ChatOpenAI(model="gpt-4o", temperature=0, api_key=config["llm"]["api_key"])

    llm_tools = llm.bind_tools(tools)
    llm_complex_tools = llm_complex.bind_tools(tools)

    builder = StateGraph(state_schema=State)

    builder.add_node("fetch_user_info", user_info_node)
    builder.set_entry_point("fetch_user_info")
    builder.add_node("finance_classifier", make_finance_classifier_node(llm_complex_tools, resource_names))
    builder.add_node("finance_qa", make_finance_qa_node(llm_tools, resource_names))
    builder.add_node("ocr_node", ocr_node(config["mistral"]["api_key"]))
    builder.add_node("router_node", router_node)
    builder.add_node("tools", build_rate_limited_tool_node(tools, min_interval=0.5))
    builder.add_node("tools_qa", build_rate_limited_tool_node(tools, min_interval=0.5))

    builder.add_edge("fetch_user_info", "router_node")
    builder.add_conditional_edges("router_node", lambda s: s["next"], {
        "ocr_node": "ocr_node",
        "finance_qa": "finance_qa"
    })
    builder.add_edge("ocr_node", "finance_classifier")
    builder.add_conditional_edges("finance_classifier", finance_phase_condition, {
        "tools": "tools", "END": END, END: END
    })
    builder.add_conditional_edges("finance_qa", tools_condition , {"tools": "tools_qa", END: END})
    builder.add_edge("tools", "finance_classifier")
    builder.add_edge("tools_qa", "finance_qa")

    return builder.compile(checkpointer=MemorySaver())
