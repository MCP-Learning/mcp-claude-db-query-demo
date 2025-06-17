MCP Claude DB Query Demo
========================

A demo project for querying a database using Claude and the Model Context Protocol (MCP).

Prerequisites
-------------

-   Python 3.13 or higher
-   (Optional) A virtual environment to keep dependencies isolated
-   API keys for Anthropic and Google Generative AI

Installation
------------

1.  **Clone the repository:**

    ```
    git clone https://github.com/yourusername/mcp-claude-db-query-demo.git
    cd mcp-claude-db-query-demo

    ```

2.  **Set up a virtual environment (recommended):**

    ```
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate

    ```

3.  **Install the project and its dependencies:**

    ```
    pip install -e .

    ```

    This uses the `pyproject.toml` file to install everything listed under `dependencies`.

Configuration
-------------

1.  **Create a `.env` file** in the project root:

    ```
    ANTHROPIC_API_KEY=your_anthropic_api_key
    GOOGLE_API_KEY=your_google_api_key

    ```

    Replace the placeholders with your actual API keys.

2.  **Database setup:**
    -   Ensure you have the SQLite database file `farming.db` at the path specified in `db_query_server.py` (default: `/Users/suhailshah/PrivateVault/projects/sandbox/AI playground/MCP/DB Query project/mcp-farming-demo/farming.db`).
    -   If the file is missing, create a sample SQLite database with tables `crops` (columns: id, farm_id, type, planting_date) and `farms` (columns: id, name, location), or adjust the path in `db_query_server.py` to match your setup.

Running the Project
-------------------

To run the project and interact with the database query system:

1.  **Ensure you are in the project root directory.**
2.  **Run the following command:**

    ```
    uv run ./client/client.py db_query_server.py

    ```

    This will start the client and connect to the database query server.

**Note:** The `uv` tool is used to manage the Python environment and run the script.

### Optional: Integration with Claude Desktop

For advanced users who want to integrate the project with Claude desktop:

1.  **Run the database query server:**

    ```
    uv run db_query_server.py

    ```

2.  **Configure Claude desktop** by updating your `claude_desktop_config.json` file. An example configuration is:

    ```
    {
        "mcpServers": {
            "db_query_server": {
                "command": "/Users/my-name/.local/bin/uv",
                "args": [
                    "--directory",
                    "/Users/my-name/path/to/the/project/mcp-claude-db-query-demo",
                    "run",
                    "db_query_server.py"
                ]
            }
        }
    }


Usage
-----
-   **Query examples:**
    -   "How many wheat are there?" (returns the count of wheat crops)
    -   "Tell me about corn" (returns details about corn crops)
    -   "What farms are there?" (lists farm details using `get_farm_info`)
-   **Exit the client:** Type 'quit' at the query prompt.

Troubleshooting
---------------

-   **Python version error**: Ensure you're using Python 3.13 or higher (`python --version`).
-   **Missing API keys**: Double-check your `.env` file if you see authentication errors.