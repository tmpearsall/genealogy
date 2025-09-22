This not production quality code

The web app was generated with Claude Code and has not been thorooughly test.

Use at your own risk.

1. Install Dependencies:
  pip install streamlit pandas plotly networkx neo4j
2. Neo4j Setup Options:
  Option A: Neo4j Desktop (Recommended for local development)
    1.	Download Neo4j Desktop
    2.	Create a new database
    3.	Start the database
    4.	Note the bolt URL (usually bolt://localhost:7687)
  Option B: Neo4j AuraDB (Cloud)
    1.	Sign up for Neo4j AuraDB (free tier available)
    2.	Create a database instance
    3.	Get connection credentials
3. Configure Credentials:
  Method 1: Streamlit Secrets (Recommended) Create .streamlit/secrets.toml:
  [neo4j]
    uri = "bolt://localhost:7687"
    username = "neo4j"
    password = "your_password"
  Method 2: Environment Variables
    export NEO4J_URI="bolt://localhost:7687"
    export NEO4J_USERNAME="neo4j"
    export NEO4J_PASSWORD="your_password"
4. Run the Application:
    streamlit run family_tree_app.py

