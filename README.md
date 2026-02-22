# Indeed Job Scraper & Resume AI

![Recruiter Clown](./recruiter_clown.png)

A comprehensive tool built to navigate an overly saturated tech job market. This CLI application streamlines your search by scraping real listings, persisting them to a vector database, and using a local LLM to generate highly customized, ATS-optimized resumes.

## Features

- **Automated Scraping**: Fetches job listings including title, company, location, salary, job type, and full job descriptions.
- **Central Manifest**: Consolidates multiple searches into a single `manifest.xlsx`, with each query getting its own tab.
- **Semantic Search**: Persists listings to a PostgreSQL database with `pgvector` for semantic similarity search using local Ollama embeddings.
- **AI Resume Generation**: Uses a local Ollama instance to rewrite your base resume for specific job postings.
- **Smart Organization**: All generated data and resumes are organized in the `output/` folder and the central manifest.

## Prerequisites

1. **Python 3.x**: Ensure you have Python installed.
2. **Docker Desktop**: Required for the PostgreSQL/pgvector database.
3. **Ollama**: Required for resume generation and embeddings.
   - Install from [ollama.com](https://ollama.com).
   - Pull necessary models:
     - `ollama pull llama3.2` (Resume generation)
     - `ollama pull nomic-embed-text` (Semantic search)

## Installation

1. **Clone and Setup**:

   ```bash
   git clone <repository-url>
   cd scrapper-indeed
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
python3 indeed_scraper.py scrape --query "Python Developer" --city "Remote" --pages 2
```

### 2. Semantic Similarity Search

Find jobs that match the _meaning_ of your query, not just keywords. Uses local vector embeddings.

```bash
python3 indeed_scraper.py similar --query "Looking for a backend role with Python and FastAPI" --top 5
```

### 3. Generating Resumes

Generate customized resumes for each job in a scraped file.

```bash
python3 indeed_scraper.py generate --input output/jobs.csv --resume my_resume.txt
```

## Infrastructure

- **Database**: PostgreSQL with `pgvector` runs on **localhost:5433**.
- **Credentials**: User: `scraper`, Password: `secret`, DB: `scraper_jobs`.
- **Manifest**: Central search history stored in `manifest.xlsx` (Project Root) and `/tmp/manifest.xlsx` (Backup).

## Project Structure

```
.
├── indeed_scraper/      # Core logic package
│   ├── db/              # Database connection and setup
│   ├── cli.py           # CLI entry point
│   ├── scraper.py       # Scraper orchestration
│   ├── parser.py        # HTML parsing
│   ├── llm.py           # AI integration (Ollama)
│   ├── db_models.py     # SQLAlchemy models
│   └── models.py        # Data dataclasses
├── docker-compose.yml   # Database infrastructure
├── indeed_scraper.py    # Main script wrapper
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Disclaimer

This tool is for educational purposes. Scraping websites like Indeed should be done responsibly and in accordance with their terms of service.
