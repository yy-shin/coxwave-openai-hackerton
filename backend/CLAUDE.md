# Backend CLAUDE.md

## Development Commands

```bash
# Run the agent CLI
uv run python app/main.py

# Run from project root
cd backend && uv run python app/main.py
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── agent.py    # Agent definitions using OpenAI Agents SDK
│   └── main.py     # CLI entry point with conversation loop
```

## Key Dependencies

- `openai-agents` - OpenAI Agents SDK for multi-agent workflows

## Architecture

### Agent Configuration (`app/agent.py`)

- Uses `Agent` class from OpenAI Agents SDK
- Model: `gpt-5.2` with high reasoning effort
- Configured with `ModelSettings` for usage tracking and reasoning

### Main Loop (`app/main.py`)

- Creates server-managed conversations via `client.conversations.create()`
- Uses `Runner.run()` for agent execution with conversation persistence
- Interactive CLI loop for user input

## Environment Variables

Required (see `.env.sample`):
- `OPENAI_API_KEY` - OpenAI API key
