"""DeFi Analyst — evaluates DeFi protocols for investment decisions.

Uses the A v0.2.4 structured output pattern: ``bind_structured`` +
``invoke_structured_or_freetext`` with a Pydantic ``DeFiAnalysis`` schema.

The analyst examines TVL metrics, protocol health, yield opportunities,
and token incentives to produce a ``PortfolioRating`` for a DeFi project.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

from tradingagents.agents.schemas import PortfolioRating
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)

logger = logging.getLogger(__name__)

AGENT_NAME = "DeFiAnalyst"


class DeFiAnalysis(BaseModel):
    """Structured DeFi protocol analysis produced by the DeFi Analyst.

    Covers TVL, protocol metrics, yield opportunities, and an overall
    rating anchored in the same 5-tier scale used by the PM.
    """

    tvl_analysis: str = Field(
        description=(
            "Analysis of Total Value Locked (TVL): current TVL, historical "
            "trends (30d/90d change), TVL ranking among peers, and what the "
            "TVL composition reveals about user confidence."
        ),
    )
    protocol_metrics: str = Field(
        description=(
            "Key protocol health metrics: revenue / fees generated, "
            "revenue-to-TVL ratio, protocol-owned liquidity, debt ratios "
            "(for lending protocols), and any relevant security / audit history."
        ),
    )
    yield_opportunities: str = Field(
        description=(
            "Available yield / APY opportunities across the protocol, "
            "token incentive sustainability, emission schedules, and "
            "comparison to competing protocols."
        ),
    )
    defi_rating: PortfolioRating = Field(
        description=(
            "The DeFi investment recommendation. Exactly one of "
            "Buy / Overweight / Hold / Underweight / Sell. "
            "Reserve Hold when evidence is balanced."
        ),
    )


def render_defi_analysis(analysis: DeFiAnalysis) -> str:
    """Render a DeFiAnalysis to markdown for storage and downstream agents."""
    return "\n".join([
        "**DeFi Analysis Report**",
        "",
        f"**TVL Analysis**: {analysis.tvl_analysis}",
        "",
        f"**Protocol Metrics**: {analysis.protocol_metrics}",
        "",
        f"**Yield Opportunities**: {analysis.yield_opportunities}",
        "",
        f"**DeFi Rating**: {analysis.defi_rating.value}",
    ])


def create_defi_analyst(llm: Any) -> Any:
    """Create a DeFi analyst node function.

    The returned closure is designed to be used as a LangGraph node.

    Args:
        llm: A LangChain-compatible LLM instance.

    Returns:
        A callable node function ``defi_analyst_node(state) -> dict``.
    """
    structured_llm = bind_structured(llm, DeFiAnalysis, AGENT_NAME)
    agent_name = AGENT_NAME

    def defi_analyst_node(state: dict) -> dict:
        """LangGraph node that produces a DeFi analysis report.

        Args:
            state: The graph state dictionary. Must contain at minimum
                ``messages`` and ``company_of_interest``.

        Returns:
            Dict with ``messages`` (appended assistant message) and
            ``defi_report`` (markdown report string).
        """
        ticker = state.get("company_of_interest", "unknown")
        instrument_context = (
            f"The DeFi protocol / crypto asset to analyze is `{ticker}`."
        )

        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from tradingagents.agents.utils.agent_utils import get_language_instruction

        system_message = (
            "You are a DeFi analyst evaluating cryptocurrency / DeFi protocols. "
            "Analyze the protocol's TVL, revenue, yield opportunities, and risks. "
            "Provide specific, actionable insights supported by evidence. "
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a helpful AI assistant collaborating with other analysts. "
                "Use the provided tools to gather DeFi data. "
                "If you are unable to fully answer, that's OK; another analyst "
                "will help where you left off. "
                "If you or any other assistant has the FINAL TRANSACTION PROPOSAL: "
                "**BUY/HOLD/SELL** or deliverable, prefix your response with "
                "FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop. "
                "You have access to the following tools: {tool_names}.\n{system_message}\n"
                "For your reference, the current date is {current_date}. {instrument_context}",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ])

        # Provide crypto data tools
        tools = []
        prompt = prompt.partial(
            system_message=system_message,
            tool_names="",
            current_date=state.get("trade_date", "unknown"),
            instrument_context=instrument_context,
        )

        chain = prompt | llm

        result = chain.invoke(state["messages"])

        report = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt.format_messages(
                system_message=system_message,
                tool_names="",
                current_date=state.get("trade_date", "unknown"),
                instrument_context=instrument_context,
                messages=state["messages"],
            ),
            render_defi_analysis,
            agent_name,
        )

        if isinstance(result, dict) and "messages" in result:
            return result

        return {
            "messages": [result],
            "defi_report": report,
        }

    return defi_analyst_node
