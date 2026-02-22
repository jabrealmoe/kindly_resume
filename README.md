# Kindly Scraper & Semantic Resume Aligner

![Recruiter Clown](./recruiter_clown.png)

A comprehensive tool built to navigate an overly saturated tech job market. This CLI application streamlines your search by scraping real listings, persisting them to a vector database, and using local LLM technology to perform **Semantic Resume Alignment**—ensuring your real-world experience is perfectly translated into the terminology that recruiters and ATS systems prioritize.

## Features

- **Automated Scraping**: Fetches job listings including title, company, location, salary, job type, and full job descriptions.
- **Central Manifest**: Consolidates multiple searches into a single `manifest.xlsx`, with each query getting its own tab.
- **Semantic Search**: Persists listings to a PostgreSQL database with `pgvector` for semantic similarity search using local Ollama embeddings.
- **Semantic Resume Alignment**: Uses a local Ollama instance to translate your base resume's accomplishments into the specific conceptual language of a job posting.
- **Smart Organization**: All generated data and resumes are organized in the `output/` folder and the central manifest.

## Responsible AI & Ethical Framing

This tool is designed for **Semantic Alignment**, not fabrication.

> [!IMPORTANT]
> **Translation, not Invention**: The goal of this tool is to bridge the "semantic gap" between how you describe your skills and how a specific company's JD describes them. It reflects your _actual_ experience using the _vocabulary_ of the target role.
>
> **User Responsibility**: Users are responsible for ensuring all final resumes accurately represent their true professional history. Do not use this tool to claim skills or experiences you do not possess.

## Prerequisites

1. **Python 3.x**: Ensure you have Python installed.
2. **Docker Desktop**: Required for the PostgreSQL/pgvector database.
3. **Ollama**: Required for alignment and embeddings.
   - Install from [ollama.com](https://ollama.com).
   - Pull necessary models:
     - `ollama pull llama3.2` (Semantic alignment)
     - `ollama pull nomic-embed-text` (Semantic search)

## Installation

1. **Clone and Setup**:

   ```bash
   git clone <repository-url>
   cd scrapper-kindly
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Start Database**:
   ```bash
   docker-compose up -d
   ```

## Usage

### 1. Scraping Jobs

Fetches jobs and saves them to the PostgreSQL database and the central `manifest.xlsx`.

```bash
python3 kindly.py scrape --query "Python Developer" --city "Remote" --pages 2
```

### 2. Semantic Similarity Search

Find jobs that match the _meaning_ of your query, not just keywords. Uses local vector embeddings.

```bash
python3 kindly.py similar --query "Looking for a backend role with Python and FastAPI" --top 5
```

### 3. Semantic Resume Alignment

Translate your resume into the specific language of a job description. Aligned resumes are automatically saved to the database.

```bash
python3 kindly.py align --input output/jobs.csv --resume my_resume.txt
```

### 4. Retrieving Aligned Resumes

Fetch a previously aligned resume from the database by its job ID.

```bash
python3 kindly.py fetch-resume --job-id 42
```

### 5. Direct Database Querying (CLI)

Query the job database directly from the CLI without writing SQL.

```bash
# List the last 10 jobs found
python3 kindly.py list-jobs --limit 10

# List jobs by company
python3 kindly.py list-jobs --company "Google"

# Show full details (description, link, etc.) for a specific job ID
python3 kindly.py describe 42
```

## Database Access

If you prefer using standard SQL tools, you can connect to the PostgreSQL instance running in Docker:

```bash
# Connect via psql
docker exec -it indeed_pg psql -U scraper -d scraper_jobs
```

- **Host**: `localhost`
- **Port**: `5433`
- **User**: `scraper`
- **Password**: `secret`
- **Database**: `scraper_jobs`

## Infrastructure

- **Database**: PostgreSQL with `pgvector` runs on **localhost:5433**.
- **Credentials**: User: `scraper`, Password: `secret`, DB: `scraper_jobs`.
- **Manifest**: Central search history stored in `manifest.xlsx` (Project Root) and `/tmp/manifest.xlsx` (Backup).

## Project Structure

```
.
├── kindly_scraper/      # Core logic package
│   ├── db/              # Database connection and setup
│   ├── cli.py           # CLI entry point
│   ├── scraper.py       # Scraper orchestration
│   ├── parser.py        # HTML parsing
│   ├── llm.py           # AI integration (Ollama)
│   ├── db_models.py     # SQLAlchemy models
│   └── models.py        # Data dataclasses
├── docker-compose.yml   # Database infrastructure
├── kindly.py            # Main script wrapper
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Disclaimer

This tool is for educational purposes. Scraping websites like Indeed should be done responsibly and in accordance with their terms of service.
