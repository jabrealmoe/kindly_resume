import subprocess
import json
import os
import re

def run_psql(query):
    cmd = [
        "psql", "-h", "localhost", "-p", "5433", "-U", "scraper", "-d", "scraper_jobs",
        "-t", "-A", "-F", "|", "-c", query
    ]
    env = os.environ.copy()
    env["PGPASSWORD"] = "secret"
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"PSQL Error: {result.stderr}")
        return None
    return result.stdout.strip()

def get_embedding(text):
    payload = {"model": "nomic-embed-text", "input": text}
    cmd = [
        "curl", "-s", "http://localhost:11434/api/embed",
        "-d", json.dumps(payload)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Ollama Error: {result.stderr}")
        return None
    try:
        data = json.loads(result.stdout)
        return data["embeddings"][0]
    except Exception as e:
        print(f"Ollama Parse Error: {e}")
        return None

def main():
    print("Fetching jobs from DB...")
    # Get ID, Title, Company, and Full Description
    output = run_psql("SELECT id, title, company, full_description FROM jobs;")
    if not output:
        print("No jobs found or error.")
        return

    lines = output.splitlines()
    print(f"Processing {len(lines)} jobs...")
    
    updates = []
    for line in lines:
        parts = line.split("|")
        if len(parts) < 4: continue
        
        job_id, title, company, desc = parts[0], parts[1], parts[2], parts[3]
        
        # Check validity
        is_valid = (
            desc 
            and not desc.startswith("Error")
            and "Description not found" not in desc
        )
        
        if is_valid:
            print(f"Re-embedding Job {job_id}: {title} at {company}")
            embed_text = f"Company: {company}\nTitle: {title}\nDescription: {desc}"
            vec = get_embedding(embed_text)
            if vec:
                # Format vector for Postgres: '[0.1, 0.2, ...]'
                vec_str = json.dumps(vec)
                updates.append(f"UPDATE jobs SET embedding = '{vec_str}' WHERE id = {job_id};")
        else:
            print(f"Nullifying Job {job_id}: {title} (Poisoned)")
            updates.append(f"UPDATE jobs SET embedding = NULL WHERE id = {job_id};")

    if updates:
        print(f"Writing {len(updates)} updates to update_embeddings.sql...")
        with open("update_embeddings.sql", "w") as f:
            for up in updates:
                f.write(up + "\n")
        
        print("Applying updates via psql...")
        # Run the SQL file
        cmd = [
            "psql", "-h", "localhost", "-p", "5433", "-U", "scraper", "-d", "scraper_jobs",
            "-f", "update_embeddings.sql"
        ]
        env = os.environ.copy()
        env["PGPASSWORD"] = "secret"
        subprocess.run(cmd, env=env)
        print("Done!")

if __name__ == "__main__":
    main()
