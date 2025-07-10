# MCP Finance Assistant

## Description

This project is a financial assistant that uses a client-server architecture to help users with their financial queries. The client is a terminal-based application built with Python and Textual, while the server is a TypeScript application that integrates with Notion to provide financial data and tools.

## Architecture

The project is divided into two main components:

- **Client**: A Python application that provides a user interface for interacting with the financial assistant. It uses the `textual` library to create a terminal-based UI and `langchain` to build a graph-based agent that can reason about financial queries.
- **Server**: A TypeScript application that exposes a set of financial tools and resources through the Model-View-Controller (MVC) pattern. It uses the `@notionhq/client` to interact with a Notion database and the `@modelcontextprotocol/sdk` to expose the tools and resources to the client.

## Features

- **Terminal-based UI**: The client provides a user-friendly terminal-based UI for interacting with the financial assistant.
- **Graph-based agent**: The client uses a graph-based agent to reason about financial queries and provide intelligent responses.
- **Notion integration**: The server integrates with Notion to provide financial data and tools.
- **Extensible**: The project is designed to be extensible, allowing new tools and resources to be added to the server and new agents to be added to the client.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 22.14.1+
- A Notion account with a database for accounts and transactions

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/mcp-finance-asistant.git
   cd mcp-finance-asistant
   ```
2. **Install the client dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Install the server dependencies**:
   ```bash
   cd servers/finance
   npm install
   ```
4. **Configure the environment variables**:
   - Create a `.env` file in the `client` directory by copying the `.env-template` file.
   - Add your Notion API key and database IDs to the `.env` file.
   - Create a `.env` file in the `servers/finance` directory and add your Notion API key and database IDs.

### Running the application

1. **Start the server**:
   ```bash
   cd servers/finance
   npm run dev
   ```
2. **Start the client**:
   ```bash
   python client/main.py
   ```

## Dependencies

### Client

- `aiolimiter`: A rate-limiting library for asyncio applications.
- `langchain-anthropic`: A library for using Anthropic models with langchain.
- `langchain-mcp-adapters`: A library for using MCP with langchain.
- `langchain-openai`: A library for using OpenAI models with langchain.
- `langgraph`: A library for building graph-based agents with langchain.
- `langsmith`: A library for debugging and testing langchain applications.
- `mcp`: The Model-View-Controller pattern for Python.
- `mistralai`: A library for using Mistral AI models.
- `pypdf2`: A library for reading and writing PDF files.
- `python-dotenv`: A library for reading environment variables from a `.env` file.
- `pyyaml`: A library for reading and writing YAML files.
- `textual`: A library for building terminal-based user interfaces.

### Server

- `@modelcontextprotocol/sdk`: The Model-View-Controller pattern for TypeScript.
- `@notionhq/client`: A client for the Notion API.
- `dotenv`: A library for reading environment variables from a `.env` file.
- `ts-node`: A TypeScript execution engine for Node.js.
- `typescript`: A typed superset of JavaScript that compiles to plain JavaScript.
