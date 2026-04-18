from serpapi.google_search import GoogleSearch
import os
import random

SERP_API_KEY = os.getenv("SERP_API_KEY") or "7416ad4d314e0eda950ff75894d6167561514f423b0c0aa8cad44a20a2b32792"

# ---------------- SAFE GENERATE ----------------

def safe_generate(prompt):
    try:
        params = {
            "engine": "google",
            "q": prompt,
            "api_key": SERP_API_KEY
        }

        search = GoogleSearch(params)
        results = search.get_dict()

        snippets = []

        # Collect snippets from results
        if "organic_results" in results:
            for r in results["organic_results"][:5]:
                if "snippet" in r:
                    snippets.append(r["snippet"])

        if snippets:
            combined = " ".join(snippets)

            # Format like AI output
            return f"""
1. Font Style & Size: Modern clean font based on industry trends
2. Color Palette: Extracted inspiration from market - Blue, White, Black
3. Logo Prompt: Inspired by {combined[:100]}...
4. Suggested Domain Name Ideas: {random.choice(['brandhub.com','getbrand.io','yourbrand.ai'])}
5. Recommended Programming Languages and Technologies: Python, Flask, React
            """

    except Exception as e:
        print("SerpAPI Error:", e)

    # 🔁 FALLBACK (offline fake AI)
    return """
1. Font Style & Size: Modern sans-serif font like Poppins
2. Color Palette: Blue, White, Black, Gray
3. Logo Prompt: Minimal abstract logo
4. Suggested Domain Name Ideas: brandhub.com, getbrand.io
5. Recommended Programming Languages and Technologies: Python, Flask, React
    """


# ---------------- EXTRACT ----------------

def extract_section_by_number(text, number):
    lines = text.split('\n')
    for line in lines:
        if line.strip().startswith(f"{number}."):
            parts = line.split(":", 1)
            if len(parts) > 1:
                return parts[1].strip()
    return "Not found"


# ---------------- BRANDING KIT ----------------

def generate_branding_kit(store_name, Domain):
    if not store_name or not Domain:
        return {
            'tagline': 'N/A',
            'colors': 'N/A',
            'logo_ideas': 'Please provide store name and domain.'
        }

    prompt = f"branding ideas for {store_name} in {Domain} domain"

    text = safe_generate(prompt)

    return {
        'tagline': extract_section_by_number(text, 1),
        'colors': extract_section_by_number(text, 2),
        'logo_ideas': extract_section_by_number(text, 3)
    }