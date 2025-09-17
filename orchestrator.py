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
		self.sql_agent = PremierLeagueSQLAgent("all_players_with_details.db")

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
		result = self.make_api_call(messages, max_tokens=2048)
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

		response = self.make_api_call(messages, max_tokens=2048)
		print(f"[GENERAL] Response received: {response[:100]}...")  # First 100 chars
		return response

	def generate_final_response(self, user_input, sql_query=None, sql_result=None):
		"""
		Use the LLM to decide what to share and how to format the response.
		Prioritize the SQL result and avoid speculative responses.
		"""
		# Build the prompt for the LLM
		prompt = (
			"You are an intelligent assistant. Based on the following information, decide what to share with the user and how to format it. "
			"Use the SQL query result as the only source of truth. Do not speculate, add, or modify any information beyond what is provided in the SQL result.\n\n"
			"SQL query result is always for 25/26 season of premier league players.\n\n"
		)
		prompt += f"User Question: {user_input}\n\n"
		if sql_query:
			prompt += f"Executed SQL Query:\n{sql_query}\n\n"
		if sql_result:
			prompt += f"SQL Query Result:\n{sql_result}\n\n"
		prompt += "Conversation History:\n"
		for prev_input, prev_response in self.conversation_history[-3:]:
			prompt += f"User: {prev_input}\nAssistant: {prev_response}\n"
		prompt += "\nProvide a clear and user-friendly response based strictly on the SQL result."

		# Call the LLM with the prompt and set temperature to 0 for deterministic responses
		response = self.make_api_call(
			[{"role": "user", "content": prompt}],
			max_tokens=10420,
			temperature=0
		)

		# Validate the LLM's response
		if "SQL Query Result" not in response:
			# Fallback to directly formatting the SQL result if the LLM response is not aligned
			if isinstance(sql_result, dict):
				import json
				formatted_json = json.dumps(sql_result, indent=4)
				return f"Here is the information you requested:\n\n```json\n{formatted_json}\n```"
			elif isinstance(sql_result, list):
				return f"Here is the list of results:\n\n{', '.join(map(str, sql_result))}"
			else:
				return str(sql_result)

		# Return the LLM's response if valid
		return response

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