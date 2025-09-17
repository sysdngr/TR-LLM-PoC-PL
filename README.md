# TransferRoom LLM Challenge – Premier League Q&A (2025/26)

This was built as part of a technical challenge for TransferRoom.  
It demonstrates how a large language model can be used to answer basic questions about Premier League players for the 2025/26 season.

---

## Data sources

Three different sources were initially considered:

- Football API – decent coverage, but with request limitations and missing fields.  
- Premier League official site (scraping) – reliable data but not always structured in a convenient way. Also included U21 and U18 without clarifying.  
- Wikipedia team pages (scraping) – broad coverage, but with occasional inconsistencies.  

In the end, I combined the Premier League site and Wikipedia, which gave a balance of coverage and reliability. 
Since the transfer window closed on September 1, 2025, the dataset should remain stable until the next window in winter. 
For this reason data-gathering procedures are not included in this prototype. :) 

---

## Architecture

The system is built around two LLM endpoints:

- **Orchestrator (GPT-5-chat)**  
  Receives user queries, interprets intent, and decides whether the question can be answered directly or requires database access.
  If sql query/result is shared, it uses this information to prepare the final response. 

- **SQL Agent (GPT-4o)**  
  When called, the orchestrator passes the query here. The SQL agent formulates an SQL query, executes it against the player database, and returns the results to the orchestrator
  

---


## UI

For the user interface, I opted for **Streamlit**. It’s lightweight and well-suited for quickly building prototypes and testing functionality.  
In a production setting, this could be replaced with a **React** frontend, which is a more common choice for scalable and maintainable applications.

---


## Design considerations

- Latency: two agents introduce extra round-trips, so answers take slightly longer.  
- Reliability: separating orchestration from querying reduces the risk of hallucinations and ensures database answers are correct.  
- Flexibility: this modular design means individual parts can be swapped or extended, e.g. using a different LLM, changing the database backend

---


## Security

This prototype does not yet include production-level security controls. In a real deployment, measures would need to be added for:  

- **SQL injection protection**
 – query safety and sanitization  
- **Prompt injection defenses** – guardrails against malicious instructions targeting the LLM  
- **Rate limiting** – to prevent abuse and excessive load  





---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/sysdngr/TR-LLM-PoC-PL.git
   ```

2. Navigate to the project directory:
   ```bash
   cd TR-LLM-PoC-PL
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the Streamlit app:
   ```bash
   streamlit run main.py
   ```

---

## Notes

This is a prototype, meant to show the overall approach rather than a production-ready system.  
If this were to move towards production, the next steps would likely include:

- More robust data pipelines that could scale beyond the Premier League to cover multiple leagues.  
- Optimizations for latency and caching so responses feel faster and more seamless.  

<img width="2526" height="2104" alt="Screenshot 2025-09-16 at 14-15-07 " src="https://github.com/user-attachments/assets/a22ed0e4-e5d1-40bf-b492-33a5a3e7f5a7" />#
