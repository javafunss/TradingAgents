"""Tokenomics Analyst — evaluates token economic models for investment decisions.

Uses the A v0.2.4 structured output pattern: ``bind_structured`` +
``invoke_structured_or_freetext`` with a Pydantic ``TokenomicsAnalysis`` schema.

The analyst examines supply dynamics, distribution, utility, and incentive
structures to produce a ``PortfolioRating`` for a crypto token.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from tradingagents.agents.schemas import PortfolioRating
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)

logger = logging.getLogger(__name__)

AGENT_NAME = "TokenomicsAnalyst"


class TokenomicsAnalysis(BaseModel):
    """Structured tokenomics analysis produced by the Tokenomics Analyst.

    Covers supply mechanics, distribution fairness, token utility, and
    an overall rating anchored in the same 5-tier scale used by the PM.
    """

    supply_analysis: str = Field(
        description=(
            "Analysis of token supply mechanics: total supply, circulating "
            "supply, inflation/deflation rate, emission schedule, burn "
            "mechanisms, and supply cap details."
        ),
    )
    distribution_analysis: str = Field(
        description=(
            "Analysis of token distribution: top holder concentration, "
            "whale wallet distribution, vesting schedules for team/VCs, "
            "liquidity pool distribution, and any centralization risks."
        ),
    )
    utility_analysis: str = Field(
        description=(
            "Analysis of token utility: use cases within the ecosystem, "
            "governance rights, fee-sharing mechanisms, staking rewards, "
            "and demand drivers for the token."
        ),
    )
    tokenomics_rating: PortfolioRating = Field(
        description=(
            "The tokenomics investment recommendation. Exactly one of "
            "Buy / Overweight / Hold / Underweight / Sell. "
            "Reserve Hold when evidence is balanced."
        ),
    )


def render_tokenomics_analysis(analysis: TokenomicsAnalysis) -> str:
    """Render a TokenomicsAnalysis to markdown for storage and downstream agents."""
    return "\n".join([
        "**Tokenomics Analysis Report**",
        "",
        f"**Supply Analysis**: {analysis.supply_analysis}",
        "",
        f"**Distribution Analysis**: {analysis.distribution_analysis}",
        "",
        f"**Utility Analysis**: {analysis.utility_analysis}",
        "",
        f"**Tokenomics Rating**: {analysis.tokenomics_rating.value}",
    ])


def create_tokenomics_analyst(llm: Any) -> Any:
    """Create a Tokenomics analyst node function.

    The returned closure is designed to be used as a LangGraph node.

    Args:
        llm: A LangChain-compatible LLM instance.

    Returns:
        A callable node function ``tokenomics_analyst_node(state) -> dict``.
    """
    structured_llm = bind_structured(llm, TokenomicsAnalysis, AGENT_NAME)
    agent_name = AGENT_NAME

    def tokenomics_analyst_node(state: dict) -> dict:
        """LangGraph node that produces a tokenomics analysis report.

        Args:
            state: The graph state dictionary. Must contain at minimum
                ``messages`` and ``company_of_interest``.

        Returns:
            Dict with ``messages`` (appended assistant message) and
            ``tokenomics_report`` (markdown report string).
        """
        ticker = state.get("company_of_interest", "unknown")
        instrument_context = (
            f"The cryptocurrency token to analyze is `{ticker}`."
        )

        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from tradingagents.agents.utils.agent_utils import get_language_instruction

        system_message = (
            "You are a tokenomics analyst evaluating cryptocurrency token economics. "
            "Analyze the token's supply mechanics, distribution fairness, utility, "
            "and incentive structures. Provide specific, actionable insights "
            "supported by evidence. "
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a helpful AI assistant collaborating with other analysts. "
                "Use the provided tools to gather tokenomics data. "
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

        prompt = prompt.partial(
            system_message=system_message,
            tool_names="",
            current_date=state.get("trade_date", "unknown"),
            instrument_context=instrument_context,
        )

        output = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt.format_messages(
                system_message=system_message,
                tool_names="",
                current_date=state.get("trade_date", "unknown"),
                instrument_context=instrument_context,
                messages=state["messages"],
            ),
            render_tokenomics_analysis,
            agent_name,
        )

        # Create a result message for the graph
        from langchain_core.messages import AIMessage
        result_msg = AIMessage(content=output)

        return {
            "messages": [result_msg],
            "tokenomics_report": output,
        }

    return tokenomics_analyst_node
