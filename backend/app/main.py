import asyncio

from agent import main_agent
from agents import Runner
from openai import AsyncOpenAI

client = AsyncOpenAI()


async def main():
    agent = main_agent

    # Create a server-managed conversation
    conversation = await client.conversations.create()
    conv_id = conversation.id

    while True:
        user_input = input("You: ")
        result = await Runner.run(agent, user_input, conversation_id=conv_id)
        print(f"Assistant: {result.final_output}")


if __name__ == "__main__":
    asyncio.run(main())
