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
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='premier_league_players_master'")
            self.table_schema = cursor.fetchone()[0]
            cursor.execute("SELECT DISTINCT club FROM premier_league_players_master")
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
            "You have access to the 'premier_league_players_master' table with this schema:\n"
            f"{self.table_schema}\n"
            "Valid club names in the database are:\n"
            f"{', '.join(self.valid_clubs)}\n"
            "Guidelines:\n"
            "1. Always identify team references in queries and map them to official club names.\n"
            "2. If a team name is ambiguous (e.g., 'Man U', 'Man United', 'ManU', 'Spurs', 'Wolves'), clarify or explain your mapping.\n"
            "3. If unsure about a team reference, ask for clarification before running SQL.\n"
            "4. Map common football position synonyms: treat 'striker' as 'forward', 'centre-back' as 'defender', 'winger' as 'forward', etc.\n"
            "5. Provide clear, football-context-aware responses.\n"
            "6. CRITICAL: Never limit or truncate results unless explicitly requested.\n"
            "If user asks for 'all players', return ALL players, not just 10 or 20. \n"
            "If user asks for 'top 40 strikers', return exactly 40 results.\n"
            "7. Always return your final answer as a JSON object with keys that match the user's request. For lists, use arrays. For tabular data, use an array of objects. Do not include any markdown, code block, or extra text—return only the raw JSON object.\n"
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
