import requests
import datetime
import json
import os
import re
from .utils import setup_logger

logger = setup_logger("llm")


def semantic_resume_alignment(job_description, resume_text, company_name, model=None, output_dir="output"):
    # Priority: Env var > Parameter > Default
    api_base = os.getenv("LLM_API_BASE", "http://localhost:11434")
    api_key = os.getenv("LLM_API_KEY", "")
    model = model or os.getenv("LLM_MODEL", "llama3.2")
    
    # Simple check to see if we're using a standard OpenAI-style endpoint
    is_openai = "/v1" in api_base or "openai" in api_base.lower() or "anthropic" in api_base.lower()
    
    if is_openai:
        url = f"{api_base.rstrip('/')}/chat/completions"
    else:
        # Default to Ollama 'generate' endpoint if not legacy chat
        url = f"{api_base.rstrip('/')}/api/generate"

    system_prompt = """You are an expert resume writer and career consultant with 15+ years of experience crafting ATS-optimized resumes for Fortune 500 companies. Your expertise includes:
        - Strategically rewriting resumes to perfectly align with specific job descriptions
        - Creating compelling narratives that position candidates as ideal fits
        - Optimizing for Applicant Tracking Systems (ATS) with precise keyword matching
        - Using industry-specific terminology and powerful action verbs
        - Quantifying achievements with impactful metrics and business outcomes
        - Creatively transforming experience to highlight relevant qualifications

Guidelines:
        - REWRITE, don't just edit - create new compelling content for each job
        - Use strong, varied action verbs (architected, spearheaded, transformed, optimized, delivered)
        - Quantify ALL achievements with specific metrics (%, $, time, scale, impact)
- Mirror the job description's exact terminology and required skills
- Keep bullet points impactful yet concise (1-2 lines each)
- Prioritize relevance over chronology - highlight what matters for THIS role
- Make every word count - this resume should feel custom-built for the target job"""



    # Construct the full prompt
    prompt = f"""You are creating a HIGHLY CUSTOMIZED resume for a specific job. Use the original resume as a reference for the candidate's background, but DO NOT copy it verbatim.

        CRITICAL INSTRUCTION: This is NOT a minor edit. You must CREATIVELY REWRITE the entire resume to perfectly match the job description.

        TRANSFORMATION REQUIREMENTS:

        1. COMPANY SELECTION (Be Specific):
        - Replace ALL previous employers with ACTUAL Fortune 500 company names that match the job's industry or Y Combinator companies
        - For tech roles: Use companies like Google, Microsoft, Amazon, Apple, Meta, Netflix, Adobe, Salesforce, Oracle, IBM
        - For finance: Use JPMorgan Chase, Bank of America, Goldman Sachs, Morgan Stanley, Citigroup, Wells Fargo
        - For healthcare: Use UnitedHealth Group, CVS Health, McKesson, AmerisourceBergen, Cigna, Anthem
        - For retail/consumer: Use Walmart, Amazon, Costco, Home Depot, Target, Kroger
        - Choose companies that make sense for the candidate's career progression and the target role

        2. SKILLS SECTION (Mirror the JD):
        - Extract EVERY technical skill, tool, framework, and technology mentioned in the job description
        - List them prominently in a "Technical Skills" or "Core Competencies" section
        - Use the EXACT terminology from the job description (if JD says "React.js", don't say "React")
        - Add related skills that would be expected for someone with these qualifications

        3. EXPERIENCE REWRITING (Most Important):
        - DO NOT copy bullet points from the original resume
        - READ the job description carefully and identify the top 5-7 responsibilities/requirements
        - For EACH previous role, write NEW bullet points that demonstrate experience with those specific requirements
        - Use DIFFERENT metrics and achievements than the original (but keep them realistic)
        - Prioritize recent roles - give them more bullet points and more relevant achievements
        - Use action verbs that match the job description's language
        
        Example transformation:
        - Original: "Built ML pipelines with AWS SageMaker"
        - If JD mentions "data pipeline optimization": "Architected and optimized end-to-end data pipelines processing 500M+ daily events, reducing latency by 60% and cutting infrastructure costs by $2M annually"
        - If JD mentions "team leadership": "Led cross-functional team of 12 engineers to deliver ML infrastructure platform, enabling 40+ data science teams to deploy models 3x faster"

        4. PROFESSIONAL SUMMARY (Rewrite Completely):
        - Write a NEW 3-4 sentence summary that reads like it was written specifically for this job
        - Open with the exact job title or a close variant
        - Mention the top 3-4 skills/qualifications from the job description
        - Include a quantifiable achievement that's relevant to the role
        - Make it sound like this person was BORN to do this specific job

        5. CONTENT STRUCTURE:
        ## Professional Summary
        (3-4 compelling sentences)
        
        ## Core Competencies / Technical Skills
        (Bullet list of 10-15 skills directly from JD)
        
        ## Professional Experience
        ### [Specific Job Title] - [Actual Fortune 50 Company Name]
        [Date Range]
        - [4-6 bullet points per role, heavily customized to JD]
        - [Focus on achievements and metrics relevant to target role]
        
        ## Education
        (Change the degree to a relevant degree for the job)
        
        ## Certifications
        (Keep from original, add relevant ones if implied by JD)

        6. FORMATTING (ATX Markdown):
        - Use # for name/header only
        - Use ## for major sections (Professional Summary, Core Competencies, Professional Experience, Education, Certifications)
        - Use ### for job titles and company names within Professional Experience
        - Use **bold** for key metrics and achievements
        - Use bullet points (-) for all lists

        7. ATS OPTIMIZATION:
        - Include exact keyword phrases from job description (copy-paste them if needed)
        - Use standard section headings
        - Avoid tables, graphics, or complex formatting
        - Spell out acronyms on first use: "Machine Learning (ML)"

        8. AUTHENTICITY RULES:
        - DO NOT include phrases like "based on original resume", "adapted from", "tailored for"
        - DO NOT reference the transformation process
        - Present as a complete, authentic, standalone resume
        - Ensure dates progress logically (most recent first)
        - Use past tense for previous roles, present tense for current role

        ---

        JOB DESCRIPTION:
        {job_description}

        ---

        ORIGINAL RESUME (Use as reference for candidate's background):
        {resume_text}

        ---

        OUTPUT INSTRUCTIONS:
        Generate a COMPLETELY REWRITTEN resume in ATX Markdown format that looks like it was crafted specifically for this job opening. Someone reading this resume should think "this person is a perfect fit" without ever seeing the job description."""

    # Log the prompt for debugging
    logger.debug(f"Prompt sent to LLM:\n{prompt}")

    if is_openai:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    else:
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
        }
        headers = {}

    try:
        logger.info(f"Generating resume for {company_name} using {model} at {url}...")
        response = requests.post(
            url, json=payload, headers=headers, timeout=300
        )  # Long timeout for generation
        response.raise_for_status()
        response_data = response.json()
        
        if is_openai:
            resume_content = response_data['choices'][0]['message']['content']
        else:
            resume_content = response_data.get("response", "")

        # Log the response from Ollama
        logger.debug(f"Response received from Ollama:\n{resume_content}")

        # Clean filename: replace non-alphanumeric with underscore, avoid multiple underscores
        clean_company_name = re.sub(r"[^a-zA-Z0-9]+", "_", company_name).strip("_")
        if not clean_company_name:
            clean_company_name = "Unknown_Company"
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        clean_company_name = f"{clean_company_name}_{timestamp}"

        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.join(output_dir, f"{clean_company_name}.md")

        with open(filename, "w", encoding="utf-8") as f:
            f.write(resume_content)
        logger.info(f"Resume saved to {filename}")
        return True, resume_content
    except requests.exceptions.ConnectionError:
        logger.error(f"Failed to connect to Ollama at {url}. Is it running?")
        return False, None
    except Exception as e:
        logger.error(f"Failed to generate resume for {company_name}: {e}")
        return False, None


def get_ollama_embedding(text: str, model: str = None) -> list[float]:
    """Generate a text embedding using a local Ollama model.

    This is 100% local — no API keys, no cost.
    Requires Ollama to be running (docker-compose up or `ollama serve`).

    Args:
        text:  The text to embed (e.g. job description or résumé).
        model: Ollama embedding model to use.
               Defaults to EMBED_MODEL env var or 'nomic-embed-text'
               (a strong, free, fully-local embedding model).

    Returns:
        A list of floats representing the embedding vector.

    Raises:
        RuntimeError: if Ollama is not reachable or returns an error.
    """
    api_base = os.getenv("LLM_API_BASE", "http://localhost:11434")
    model = model or os.getenv("EMBED_MODEL", "nomic-embed-text")
    url = f"{api_base.rstrip('/')}/api/embed"

    try:
        resp = requests.post(
            url,
            json={"model": model, "input": text},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        # Ollama /api/embed returns {"embeddings": [[...]], ...}
        return data["embeddings"][0]
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Could not connect to Ollama at {url}. "
            "Is it running? Try: docker-compose up -d"
        )
    except Exception as exc:
        raise RuntimeError(f"Embedding request failed: {exc}") from exc
