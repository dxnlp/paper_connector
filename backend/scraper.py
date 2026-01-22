"""
Hugging Face Papers Scraper.
Fetches papers from HF monthly listing and extracts metadata from paper pages.
"""

import httpx
import re
import json
from bs4 import BeautifulSoup
from typing import Optional
from database import Paper, compute_content_hash

HF_BASE_URL = "https://huggingface.co"


async def fetch_month_paper_ids(month: str) -> list[str]:
    """
    Fetch all paper IDs from a monthly listing page.
    
    Args:
        month: Month string in format YYYY-MM (e.g., "2025-01")
    
    Returns:
        List of arxiv paper IDs
    """
    url = f"{HF_BASE_URL}/papers/month/{month}"
    paper_ids = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Find all paper links - they follow pattern /papers/XXXX.XXXXX
        paper_links = soup.find_all('a', href=re.compile(r'^/papers/\d{4}\.\d{4,5}$'))
        
        for link in paper_links:
            href = link.get('href', '')
            match = re.search(r'/papers/(\d{4}\.\d{4,5})', href)
            if match:
                paper_id = match.group(1)
                if paper_id not in paper_ids:
                    paper_ids.append(paper_id)
        
        # Also try to extract from script tags (HF sometimes uses JSON data)
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'papers' in script.string.lower():
                # Try to find arxiv IDs in JSON data
                ids_in_script = re.findall(r'"(\d{4}\.\d{4,5})"', script.string)
                for pid in ids_in_script:
                    if pid not in paper_ids:
                        paper_ids.append(pid)
    
    return paper_ids


async def fetch_paper_details(paper_id: str) -> Optional[Paper]:
    """
    Fetch detailed information for a single paper from its HF page.
    
    Args:
        paper_id: The arxiv ID (e.g., "2512.24880")
    
    Returns:
        Paper object with all metadata, or None if fetch fails
    """
    url = f"{HF_BASE_URL}/papers/{paper_id}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as e:
            print(f"Failed to fetch paper {paper_id}: {e}")
            return None
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Extract title - usually in h1 or main heading
        title = ""
        title_elem = soup.find('h1')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        # Extract abstract - look for the abstract section
        abstract = ""
        # Try multiple selectors for abstract
        abstract_selectors = [
            ('p', {'class': re.compile(r'abstract', re.I)}),
            ('div', {'class': re.compile(r'abstract', re.I)}),
            ('section', {'id': 'abstract'}),
        ]
        
        for tag, attrs in abstract_selectors:
            elem = soup.find(tag, attrs)
            if elem:
                abstract = elem.get_text(strip=True)
                break
        
        # If no abstract found, try to find it in meta tags
        if not abstract:
            meta_desc = soup.find('meta', {'name': 'description'})
            if meta_desc:
                abstract = meta_desc.get('content', '')
        
        # Try to find abstract in the page content
        if not abstract:
            # Look for text that looks like an abstract (long paragraph after title)
            main_content = soup.find('main') or soup.find('article') or soup.body
            if main_content:
                paragraphs = main_content.find_all('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    # Abstract is usually a substantial paragraph
                    if len(text) > 200 and not text.startswith('http'):
                        abstract = text
                        break
        
        # Extract upvotes - look for upvote count
        upvotes = 0
        upvote_elem = soup.find(string=re.compile(r'^\d+$'))
        if upvote_elem:
            parent = upvote_elem.find_parent()
            if parent and ('upvote' in str(parent).lower() or 'like' in str(parent).lower()):
                try:
                    upvotes = int(upvote_elem.strip())
                except ValueError:
                    pass
        
        # Try to find upvotes in various places
        for elem in soup.find_all(['span', 'div', 'button']):
            classes = elem.get('class', [])
            text = elem.get_text(strip=True)
            if any('upvote' in c.lower() or 'like' in c.lower() for c in classes if isinstance(c, str)):
                try:
                    upvotes = int(re.search(r'\d+', text).group())
                    break
                except (ValueError, AttributeError):
                    pass
        
        # Extract authors
        authors = []
        # Look for author links or spans
        author_section = soup.find(class_=re.compile(r'author', re.I))
        if author_section:
            author_links = author_section.find_all('a')
            authors = [a.get_text(strip=True) for a in author_links if a.get_text(strip=True)]
        
        if not authors:
# Try meta tags
            meta_authors = soup.find_all('meta', {'name': 'author'})
            authors = [m.get('content', '') for m in meta_authors if m.get('content')]
        
        # Extract published date
        published_date = ""
        date_elem = soup.find('time')
        if date_elem:
            published_date = date_elem.get('datetime', '') or date_elem.get_text(strip=True)
        
        # Build URLs
        hf_url = url
        arxiv_url = f"https://arxiv.org/abs/{paper_id}"
        pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
        
        # Compute content hash for change detection
        content_hash = compute_content_hash(title, abstract)
        
        return Paper(
            id=paper_id,
            title=title,
            abstract=abstract,
            published_date=published_date,
            hf_url=hf_url,
            arxiv_url=arxiv_url,
            pdf_url=pdf_url,
            upvotes=upvotes,
            authors=authors,
            content_hash=content_hash
        )


async def scrape_month(month: str, progress_callback=None) -> list[Paper]:
    """
    Scrape all papers for a given month.
    
    Args:
        month: Month string in format YYYY-MM
        progress_callback: Optional callback(current, total, paper_id) for progress updates
    
    Returns:
        List of Paper objects
    """
    print(f"Fetching paper list for month {month}...")
    paper_ids = await fetch_month_paper_ids(month)
    print(f"Found {len(paper_ids)} papers")
    
    papers = []
    for i, paper_id in enumerate(paper_ids):
        if progress_callback:
            progress_callback(i + 1, len(paper_ids), paper_id)
        
        print(f"Fetching paper {i + 1}/{len(paper_ids)}: {paper_id}")
        paper = await fetch_paper_details(paper_id)
        if paper:
            papers.append(paper)
    
    return papers


# For testing
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Test with a sample month
        papers = await scrape_month("2025-01")
        for p in papers[:5]:
            print(f"\n{p.id}: {p.title[:50]}...")
            print(f"  Upvotes: {p.upvotes}")
            print(f"  Abstract: {p.abstract[:100]}...")
    
    asyncio.run(main())
