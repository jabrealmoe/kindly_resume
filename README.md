# Indeed Job Scraper & Resume AI

![Recruiter Clown](./recruiter_clown.png)

A comprehensive tool built to navigate an overly saturated tech job market and counter the noise of constant, unproductive outreach from "clown" agencies—specifically designed as a robust defense against the flood of ghost-job recruiting calls. This CLI application streamlines your search by scraping real listings and using a local LLM to generate highly customized, ATS-optimized resumes.

This tool is designed to be highly extensible and is a powerful skill to be used in conjunction with automation frameworks like **OpenClaw**.

## Features

- **Automated Scraping**: Fetches job listings including title, company, location, and full job descriptions.
- **AI Resume Generation**: Uses a local Ollama instance (e.g., Llama 3.2) to rewrite your base resume for specific job postings.
- **Smart Organization**: All generated data, scrapes, and resumes are neatly organized in a consolidated `output/` folder.
- **Robustness**: Handles pagination, redirects, retries with exponential backoff, and randomized headers to navigate anti-bot measures.

## Prerequisites

1. **Python 3.x**: Ensure you have Python installed.
2. **Ollama**: Required for resume generation.
   - Install from [ollama.com](https://ollama.com).
   - Pull the default model: `ollama pull llama3.2`

## Installation

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd scrapper-indeed
   ```

2. **Set up virtual environment**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

The tool is accessible via two main commands: `scrape` and `generate`.

### 1. Scraping Jobs

Fetch jobs and save them for later processing. Results are stored in `output/` by default.

```bash
python3 indeed_scraper.py scrape --query "Python Developer" --city "Atlanta, GA" --days 7 --pages 3
```

**Options:**

- `--query`: Job search keywords (Required).
- `--city`: Target location (Required).
- `--days`: Limit to jobs posted within the last N days (Default: 7).
- `--pages`: Number of pages to scrape (Default: 5).
- `--output`: Custom filename (e.g., `my_jobs.csv`). Saved in `output/` by default.
- `--format`: `csv` or `json` (Default: `csv`).

### 2. Generating Resumes

Generate customized resumes for each job in a scraped file.

```bash
python3 indeed_scraper.py generate --input output/jobs.csv --resume my_resume.txt
```

**Options:**

- `--input`: Path to the scraped jobs file (Required).
- `--resume`: Path to your base resume in text format (Required).
- `--model`: The Ollama model to use (Default: `llama3.2`).
- `--output-dir`: Custom directory for generated resumes (Default: `output`).

## Output Structure

All generated files are consolidated into the `output/` directory (ignored by git):

- `output/*.csv`: Scraped job data.
- `output/*.md`: AI-generated, job-specific resumes.

## Project Structure

```
.
├── indeed_scraper/      # Core logic package
│   ├── cli.py           # CLI entry point and command definitions
│   ├── scraper.py       # Scraper orchestration
│   ├── parser.py        # HTML parsing and extraction
│   ├── llm.py           # AI integration (Ollama)
│   ├── models.py        # Data models
│   └── utils.py         # Shared helpers
├── output/              # Consolidated generated folder (local only)
├── indeed_scraper.py    # Main script wrapper
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Disclaimer

This tool is for educational purposes. Scraping websites like Indeed should be done responsibly and in accordance with their terms of service. Over-aggressive scraping may lead to IP blocks or CAPTCHAs.
