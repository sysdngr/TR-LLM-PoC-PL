import os
import requests
import json
from sql_agent import PremierLeagueSQLAgent

class LLMOrchestrator:
	def _stringify(self, value):
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

	def classify_query(self, user_input):
		"""
		Uses LLM with a system prompt to classify the query.
		Returns: "general" or "sql_required"
		"""
		print(f"\n[CLASSIFY] Input: {user_input}")
		
		system_prompt = (
			"You are an expert assistant. "
			"If the user's query is about Premier League players or teams, especially for the 2025/2026 season, "
			"reply ONLY with 'sql_required'. If not, reply ONLY with 'general'. Do not explain your answer."
		)
		url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
		headers = {"Content-Type": "application/json", "api-key": self.key}
		messages = [
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_input}
		]
		payload = {
			"messages": messages,
			"max_tokens": 128,
			"model": self.model
		}
		print("[CLASSIFY] Sending classification request to LLM...")
		resp = requests.post(url, headers=headers, json=payload, timeout=10)
		if resp.ok:
			data = resp.json()
			result = data["choices"][0]["message"]["content"].strip().lower()
			print(f"[CLASSIFY] LLM response: {result}")
			if "sql_required" in result:
				return "sql_required"
			return "general"
		else:
			print(f"[CLASSIFY] Error: {resp.text}")
			return "general"  # fallback

	def handle_general_query(self, user_input, context=None):
		"""
		Calls Azure OpenAI for general queries.
		"""
		print(f"\n[GENERAL] Processing general query: {user_input}")
		if context:
			print(f"[GENERAL] With context: {context}")
		
		url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
		headers = {"Content-Type": "application/json", "api-key": self.key}
		messages = []

		# Add conversation history
		history_count = len(self.conversation_history[-3:])
		if history_count > 0:
			print(f"[GENERAL] Adding {history_count} historical messages...")
			for prev_input, prev_response in self.conversation_history[-3:]:
				messages.extend([
					{"role": "user", "content": self._stringify(prev_input)},
					{"role": "assistant", "content": self._stringify(prev_response)}
				])

		# Add current context and query
		if context:
			messages.append({"role": "system", "content": self._stringify(context)})
		messages.append({"role": "user", "content": self._stringify(user_input)})
		
		payload = {
			"messages": messages,
			"max_tokens": 512,
			"model": self.model
		}
		
		print("[GENERAL] Sending request to LLM...")
		resp = requests.post(url, headers=headers, json=payload, timeout=20)
		if resp.ok:
			data = resp.json()
			response = data["choices"][0]["message"]["content"]
			print(f"[GENERAL] Response received: {response[:100]}...")  # First 100 chars
			return response
		else:
			error = f"[ERROR] {resp.text}"
			print(f"[GENERAL] Error: {error}")
			return error

	def generate_final_response(self, user_input, sql_query=None, sql_result=None):
		"""
		If SQL query and result are present, generate a summary for structured/tabular data using LLM, unless the data is trivially simple.
		Otherwise, use LLM for general queries.
		"""
		if sql_query and sql_result:
			import pandas as pd
			summary = None
			if isinstance(sql_result, dict):
				for key, value in sql_result.items():
					if isinstance(value, list) and value:
						if len(value) > 2:
							df = pd.DataFrame(value)
							context = (
								f"User question: {user_input}\n"
								f"Here is the data returned from the database as a table:\n{df.to_string(index=False)}\n"
								"If the data is self-explanatory, you may simply say so. Otherwise, provide a brief summary or insight for the user."
							)
							summary = self.handle_general_query(user_input, context=context)
						break
			if summary:
				return {"summary": summary.strip(), "data": sql_result}
			else:
				return sql_result
		else:
			return self.handle_general_query(user_input)

	def process_sql_query(self, user_input):
		"""
		Main orchestration method: classifies query and triggers SQL agent if needed.
		"""
		print(f"\n[PROCESS] Starting to process query: {user_input}")
		
		query_type = self.classify_query(user_input)
		print(f"[PROCESS] Query classified as: {query_type}")
		
		if query_type == "sql_required":
			# Get recent conversation context
			recent_context = self.conversation_history[-3:]  # Last 3 turns
			context_count = len(recent_context)
			print(f"[PROCESS] Using {context_count} recent conversation turns...")
			
			print("[PROCESS] Initializing SQL agent...")
			sql_agent = PremierLeagueSQLAgent("premier_league_players_master.db")
			sql_query = user_input
			print("[PROCESS] Running SQL agent...")
			sql_result = sql_agent.run(user_input, conversation_history=recent_context)
			print(f"[PROCESS] SQL agent result received: {str(sql_result)[:100]}...")  # First 100 chars

			# Handle agent reply with 'output' key containing JSON string
			import json
			parsed_result = None
			if isinstance(sql_result, dict) and "output" in sql_result:
				output_val = sql_result["output"]
				try:
					parsed_result = json.loads(output_val)
				except Exception:
					parsed_result = output_val
			elif isinstance(sql_result, str):
				try:
					parsed_result = json.loads(sql_result)
				except Exception:
					parsed_result = sql_result
			else:
				parsed_result = sql_result

			print("[PROCESS] Generating final response...")
			response = self.generate_final_response(user_input, sql_query, parsed_result)
			self.conversation_history.append((user_input, response))
			print("[PROCESS] Response added to conversation history")
			return response
		else:
			print("[PROCESS] Handling as general query...")
			response = self.generate_final_response(user_input)
			self.conversation_history.append((user_input, response))
			print("[PROCESS] Response added to conversation history")
			return response