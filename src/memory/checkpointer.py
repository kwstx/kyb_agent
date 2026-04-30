import os
from langgraph.checkpoint.memory import MemorySaver
# In a real environment, you'd use PostgresSaver or MongoDBSaver
# from langgraph.checkpoint.postgres import PostgresSaver

def get_checkpointer():
    """Returns a LangGraph checkpointer for short-term conversational memory."""
    # Default to MemorySaver for simplicity in this environment
    # but designed to be easily swapped for PostgresSaver
    return MemorySaver()

# Example of how PostgresSaver would be initialized:
# def get_postgres_checkpointer(conn_string: str):
#     return PostgresSaver.from_conn_string(conn_string)
