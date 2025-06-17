from typing import Any
import sqlite3
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("db_query_server")

# Constants
DB_PATH = "/Users/suhailshah/PrivateVault/projects/sandbox/AI playground/MCP/DB Query project/mcp-farming-demo/farming.db"

def execute_query(query: str, params: tuple = ()) -> list:
    """Execute a SQL query and return the results."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return results

@mcp.tool()
async def get_crop_info(crop_type: str) -> str:
    """Retrieve detailed information about crops of a specific type, such as wheat or corn. 
    This includes the number of crops planted, their planting dates, and the farms they are associated with.

    Use this tool for queries like 'how many wheat crops are there?' or 'tell me about corn'.

    Args:
        crop_type: The type of crop to query (e.g., 'wheat', 'corn'). This parameter is required.
    """
    query = "SELECT * FROM crops WHERE type = ?"
    results = execute_query(query, (crop_type,))
    if not results:
        return f"No information found for crop type: {crop_type}"
    crop_info = "\n".join([f"ID: {row[0]}, Type: {row[2]}, Planting Date: {row[3]}, Farm ID: {row[1]}" for row in results])
    return crop_info

@mcp.tool()
async def get_farm_info(farm_id: int) -> str:
    """Get information about a specific farm.

    Args:
        farm_id: ID of the farm to query
    """
    query = "SELECT * FROM farms WHERE id = ?"
    results = execute_query(query, (farm_id,))
    if not results:
        return f"No information found for farm ID: {farm_id}"
    farm_info = "\n".join([f"ID: {row[0]}, Name: {row[1]}, Location: {row[2]}" for row in results])
    return farm_info


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')