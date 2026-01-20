from agents import Agent, ModelSettings
from openai.types.shared import Reasoning

INSTRUCTION = """You're a helpful agent."""

main_agent = Agent(
    name="main_agent",
    instructions=INSTRUCTION,
    model="gpt-5.2",
    model_settings=ModelSettings(
        include_usage=True, reasoning=Reasoning(effort="high"), verbosity="low"
    ),
    tools=[],
    handoffs=[],
)
