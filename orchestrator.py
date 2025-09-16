import os
import requests
import json
from sql_agent import PremierLeagueSQLAgent

class LLMOrchestrator:
	def stringify(self, value):
		if isinstance(value, (dict, list)):
			try:
				return json.dumps(value)
			except Exception:
				return str(value)
		return str(value)


	def __init__(self):
		# Load Azure OpenAI config from environment
		self.endpoint   = os.environ.get("AZURE_OPENAI_MAIN_ENDPOINT")
		self.key        = os.environ.get("AZURE_OPENAI_MAIN_KEY")
		self.deployment = os.environ.get("AZURE_OPENAI_MAIN_DEPLOYMENT")
		self.api_version= os.environ.get("AZURE_OPENAI_MAIN_API_VERSION")
		self.model      = os.environ.get("OPENAI_MODEL_MAIN")
		# Initialize conversation history
		self.conversation_history = []  # List of (user_input, response) tuples
		self.sql_agent = PremierLeagueSQLAgent("premier_league_players_master.db")

	def make_api_call(self, messages, max_tokens):
		"""
		Helper method to make API calls to avoid duplication in classify + handle_general
		Args:
			messages (list): The messages to send in the API request.
			max_tokens (int): The maximum number of tokens for the response.
		Returns:
			str: The response content from the API, or an error message.
		"""
		url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
		headers = {"Content-Type": "application/json", "api-key": self.key}
		payload = {
			"messages": messages,
			"max_tokens": max_tokens,
			"model": self.model
		}
		try:
			print("[API CALL] Sending request to Azure OpenAI...")
			resp = requests.post(url, headers=headers, json=payload, timeout=30)
			resp.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
			data = resp.json()
			return data["choices"][0]["message"]["content"].strip()
		except requests.exceptions.RequestException as e:
			print(f"[API CALL] Error: {str(e)}")
			return f"[ERROR] {str(e)}"

	def classify_query(self, user_input):
		"""
		Classify the user query as either 'general' or 'sql_required'.
		"""
		print(f"\n[CLASSIFY] Input: {user_input}")
		system_prompt = (
			"You are an expert assistant. "
			"If the user's query is about Premier League players or teams, especially for the 2025/2026 season, "
			"reply ONLY with 'sql_required'. If not, reply ONLY with 'general'. Do not explain your answer."
		)
		messages = [
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_input}
		]
		result = self.make_api_call(messages, max_tokens=128)
		print(f"[CLASSIFY] LLM response: {result}")
		return "sql_required" if "sql_required" in result.lower() else "general"

	def execute_query(self, user_input):
		"""
		Execute the SQL query using the SQL agent and return the results.
		"""
		print("[EXECUTE] Running SQL agent...")
		recent_context = self.conversation_history[-3:]  # Last 3 turns
		sql_result = self.sql_agent.run(user_input, conversation_history=recent_context)
		print(f"[EXECUTE] SQL agent result received: {str(sql_result)[:100]}...")  # First 100 chars
		return sql_result

	def generate_response(self, user_input, sql_result=None):
		"""
		Generate the final response based on the query type and results.
		"""
		if sql_result:
			return self.handle_general_query(user_input, context=sql_result)
		return self.handle_general_query(user_input)

	def handle_general_query(self, user_input, context=None):
		"""
		Calls Azure OpenAI for general queries.
		"""
		print(f"\n[GENERAL] Processing general query: {user_input}")
		if context:
			print(f"[GENERAL] With context: {context}")
		
		messages = []

		# Add conversation history
		history_count = len(self.conversation_history[-3:])
		if history_count > 0:
			print(f"[GENERAL] Adding {history_count} historical messages...")
			for prev_input, prev_response in self.conversation_history[-3:]:
				messages.extend([
					{"role": "user", "content": self.stringify(prev_input)},
					{"role": "assistant", "content": self.stringify(prev_response)}
				])

		# Add current context and query
		if context:
			messages.append({"role": "system", "content": self.stringify(context)})
		messages.append({"role": "user", "content": self.stringify(user_input)})

		response = self.make_api_call(messages, max_tokens=512)
		print(f"[GENERAL] Response received: {response[:100]}...")  # First 100 chars
		return response

	def generate_final_response(self, user_input, sql_query=None, sql_result=None):
		"""
		Strictly return SQL results without any speculative follow-up offers or additional commentary.
		Format the JSON output in a user-friendly way.
		"""
		if sql_result:
			import json
			if isinstance(sql_result, dict):
				# Prettify JSON output for user-friendly display
				formatted_json = json.dumps(sql_result, indent=4)
				return f"Here is the information you requested:\n\n```json\n{formatted_json}\n```"
			elif isinstance(sql_result, list):
				# Handle list results if applicable
				return f"Here is the list of results:\n\n{', '.join(map(str, sql_result))}"
			else:
				return str(sql_result)
		
		# Fallback to general query handling only if no SQL result is available
		return self.handle_general_query(user_input)

	def process_query(self, user_input):
		"""
		Main entry point for processing user queries.
		"""
		print(f"\n[PROCESS] Starting to process query: {user_input}")
		query_type = self.classify_query(user_input)
		if query_type == "sql_required":
			sql_result = self.execute_query(user_input)
			response = self.generate_response(user_input, sql_result)
		else:
			response = self.generate_response(user_input)
		self.conversation_history.append((user_input, response))
		self.conversation_history = self.conversation_history[-10:]  # Limit history to last 10 entries
		print("[PROCESS] Response added to conversation history")
		return response