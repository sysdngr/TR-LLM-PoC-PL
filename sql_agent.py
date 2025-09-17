# This module defines the `PremierLeagueSQLAgent` class.
# It connects to an SQLite database and uses Azure OpenAI to process SQL queries.
# Includes methods for validating environment variables, initializing the database schema,
# and building prompts for querying Premier League data.

import os
import sqlite3
from langchain_openai import AzureChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain.agents.agent_types import AgentType

class PremierLeagueSQLAgent:
    def __init__(self, db_path):
        self.db_path = db_path
        self.db_uri = f"sqlite:///{db_path}"

        # Azure OpenAI config from environment
        self.endpoint = os.environ.get("AZURE_OPENAI_SQL_ENDPOINT")
        self.key = os.environ.get("AZURE_OPENAI_SQL_KEY")
        self.deployment = os.environ.get("AZURE_OPENAI_SQL_DEPLOYMENT")
        self.api_version = os.environ.get("AZURE_OPENAI_SQL_API_VERSION")
        self.model = os.environ.get("OPENAI_MODEL_SQL")

        self.validate_environment_variables()

        self.llm = AzureChatOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.key,
            deployment_name=self.deployment,
            api_version=self.api_version,
            model=self.model,
            max_tokens=10420 
        )

        self.db = SQLDatabase.from_uri(self.db_uri)
        self.init_schema()
        self.agent = create_sql_agent(
            llm=self.llm,
            db=self.db,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            verbose=True,
            handle_parsing_errors=True
        )

    def validate_environment_variables(self):
        missing_vars = [
            var for var in ["AZURE_OPENAI_SQL_ENDPOINT", "AZURE_OPENAI_SQL_KEY", "AZURE_OPENAI_SQL_DEPLOYMENT", "AZURE_OPENAI_SQL_API_VERSION", "OPENAI_MODEL_SQL"]
            if not os.environ.get(var)
        ]
        if missing_vars:
            raise ValueError(f"Missing Azure OpenAI SQL environment variables: {', '.join(missing_vars)}")

    def init_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='all_players_with_details'")
            self.table_schema = cursor.fetchone()[0]
            cursor.execute("SELECT DISTINCT [Team Name] FROM all_players_with_details")
            self.valid_clubs = [row[0] for row in cursor.fetchall()]

    def build_prompt(self, user_query, conversation_history):
        history_context = ""
        if conversation_history:
            history_context = "Previous conversation for context:\n"
            for prev_query, prev_response in conversation_history:
                history_context += f"User: {prev_query}\nAssistant: {prev_response}\n"
            history_context += "\nConsider this context for the current question.\n"

        return (
            "You are an expert Premier League SQL agent for the 2025/2026 season. "
            "You understand football culture, player information, and common terminology.\n"
            "You have access to the 'all_players_with_details' table with this schema:\n"
            f"{self.table_schema}\n"
            "Valid team names in the database are:\n"
            f"{', '.join(self.valid_clubs)}\n"
            "Guidelines:\n"
            "1. Map team references to official club names (e.g., 'Man U' -> 'Manchester United').\n"
            "2. Clarify ambiguous team names or positions before running SQL.\n"
            "3. Use synonyms for positions (e.g., 'striker' -> 'forward', 'centre-back' -> 'defender').\n"
            "4. Return only relevant columns based on the user’s request. Default to player name, position, and team unless specified otherwise.\n"
            "5. Do not truncate results unless explicitly requested (e.g., 'top 10 players').\n"
            "6. Always return results as a JSON object with keys matching the user’s request.\n"
            "7. Avoid verbose or unnecessary fields in the response.\n"
            f"{history_context}User query: {user_query}"
        )

    def run(self, user_query, conversation_history=None):
        """
        Run a user query using the SQL agent, with optional conversation history for context.
        Args:
            user_query (str): The user's question about Premier League data
            conversation_history (list, optional): List of (query, response) tuples
        Returns:
            str: Agent's response
        """
        try:
            prompt = self.build_prompt(user_query, conversation_history)
            result = self.agent.invoke(prompt)
            # Clean the response - extract JSON from agent wrapper
            if isinstance(result, dict) and 'output' in result:
                return result['output']
            return result
        except Exception as e:
            return {"error": f"SQL Agent Error: {str(e)}"}
