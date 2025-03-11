import requests
import pandas as pd
import time
from bs4 import BeautifulSoup

def fetch_papers(query, max_retries=3, delay=5):
    """Fetches research papers from PubMed API with retry handling."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": 5  # Fetch up to 5 results to reduce API load
    }

    for attempt in range(max_retries):
        try:
            print(f"🔄 Fetching papers for query: {query} (Attempt {attempt + 1})")
            response = requests.get(base_url, params=params, timeout=30)  # Increased timeout
            response.raise_for_status()

            paper_ids = response.json().get("esearchresult", {}).get("idlist", [])
            if not paper_ids:
                print("❌ No papers found. Exiting.")
                return []
            print(f"✅ Fetched Paper IDs: {paper_ids}")
            return paper_ids

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching papers: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("❌ Failed to fetch papers after multiple attempts.")
                return []

def get_paper_details(paper_ids, max_retries=3, delay=5):
    """Fetches details of research papers with retry handling."""
    details_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(paper_ids),
        "retmode": "json"
    }

    for attempt in range(max_retries):
        try:
            print(f"🔄 Fetching details for {len(paper_ids)} papers (Attempt {attempt + 1})")
            response = requests.get(details_url, params=params, timeout=30)  # Increased timeout
            response.raise_for_status()

            return response.json().get("result", {})

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching paper details: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("❌ Failed to fetch paper details after multiple attempts.")
                return {}

def get_author_affiliations(paper_id, max_retries=3, delay=5):
    """Fetches authors and affiliations for a given PubMed paper ID with retry handling."""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": paper_id,
        "retmode": "xml"
    }

    for attempt in range(max_retries):
        try:
            print(f"🔄 Fetching authors for paper {paper_id} (Attempt {attempt + 1})")
            response = requests.get(url, params=params, timeout=30)  # Increased timeout
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "xml")
            authors = []
            affiliations = []

            for author in soup.find_all("Author"):
                last_name = author.find("LastName")
                fore_name = author.find("ForeName")
                affiliation = author.find_next("Affiliation")

                author_name = f"{fore_name.text if fore_name else ''} {last_name.text if last_name else ''}".strip()
                authors.append(author_name)

                if affiliation:
                    affiliations.append(affiliation.text)

            return authors, affiliations

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching authors for {paper_id}: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("❌ Failed to fetch author details after multiple attempts.")
                return [], []

def is_non_academic_affiliation(affiliations):
    """Checks if at least one author is from a pharmaceutical or biotech company."""
    keywords = ["pharma", "biotech", "laboratories", "inc.", "corporation", "company", "llc", "ltd"]
    return any(any(keyword in aff.lower() for keyword in keywords) for aff in affiliations)

if __name__ == "__main__":
    print("✅ Script started. Waiting for input...")
    query = input("Enter your search query: ").strip()
    print(f"✅ Query received: {query}")

    paper_ids = fetch_papers(query)
    if not paper_ids:
        print("❌ No papers found. Exiting.")
        exit()

    paper_data = get_paper_details(paper_ids)
    if not paper_data:
        print("❌ No paper details fetched. Exiting.")
        exit()

    filtered_papers = []
    for paper_id in paper_ids:
        if paper_id in paper_data:
            title = paper_data[paper_id].get("title", "No Title Available")
            pub_date = paper_data[paper_id].get("pubdate", "No Date Available")

            authors, affiliations = get_author_affiliations(paper_id)

            if is_non_academic_affiliation(affiliations):
                filtered_papers.append({
                    "Paper ID": paper_id,
                    "Title": title,
                    "Publication Date": pub_date,
                    "Authors": "; ".join(authors),
                    "Affiliations": "; ".join(affiliations)
                })

    if filtered_papers:
        df = pd.DataFrame(filtered_papers)
        df.to_csv("filtered_papers.csv", index=False, encoding="utf-8")
        print("\n✅ Papers with at least one non-academic affiliation saved to 'filtered_papers.csv'.")
    else:
        print("\n❌ No papers found with non-academic authors.")
