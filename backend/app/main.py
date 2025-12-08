from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Set, AsyncGenerator
import requests
from bs4 import BeautifulSoup
import uuid
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
import logging
from pydantic import BaseModel
import os
import json
import asyncio
import trafilatura

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Web Scraping API",
    description="A FastAPI-based web scraping API that crawls websites and extracts article content - Made by Eng: Amr Hossam",
    version="1.0.0"
)

# أضف عناوين Frontend المسموح لها بالاتصال - عدّل هنا قبل البناء
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://YOUR-ACTUAL-FRONTEND-URL.com").split(",")
IS_WILDCARD_ORIGINS = ALLOWED_ORIGINS == ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if IS_WILDCARD_ORIGINS else ALLOWED_ORIGINS,
    allow_credentials=not IS_WILDCARD_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScrapedPage(BaseModel):
    data: Dict[str, Any]

class WebScraper:
    def __init__(self, base_url: str, timeout: int = 10, max_pages: int = 100, callback=None):
        self.base_url = base_url
        self.timeout = timeout
        self.max_pages = max_pages
        self.visited_urls: Set[str] = set()
        self.session = requests.Session()
        self.callback = callback
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        parsed_url = urlparse(base_url)
        self.domain = parsed_url.netloc
        self.scheme = parsed_url.scheme
    
    def is_same_domain(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            return parsed.netloc == self.domain or parsed.netloc == f"www.{self.domain}" or parsed.netloc == self.domain.replace("www.", "")
        except Exception:
            return False
    
    def normalize_url(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            normalized = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path.rstrip('/') if parsed.path != '/' else parsed.path,
                parsed.params,
                parsed.query,
                ''
            ))
            return normalized
        except Exception:
            return url
    
    def extract_links(self, html_content: str, base_url: str) -> Set[str]:
        links = set()
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for link in soup.find_all('a', href=True):
                href_attr = link.get('href')
                if not href_attr:
                    continue
                href = str(href_attr).strip()
                if not href or href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
                    continue
                
                absolute_url = urljoin(base_url, href)
                
                if self.is_same_domain(absolute_url) and not self.is_duplicate_url(absolute_url):
                    normalized_url = self.normalize_url(absolute_url)
                    links.add(normalized_url)
        
        except Exception as e:
            logger.error(f"Error extracting links: {e}")
        
        return links
    
    def normalize_url_for_deduplication(self, url: str) -> str:
        try:
            parsed = urlparse(url.lower().strip())
            
            query_params = parse_qs(parsed.query)
            filtered_params = {}
            
            tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 
                             'fbclid', 'gclid', 'ref', 'source', '_ga', '_gl', 'mc_cid', 'mc_eid',
                             'campaign', 'medium', 'content', 'term', 'msclkid', 'wbraid', 'gbraid'}
            
            for key, value in query_params.items():
                if key.lower() not in tracking_params:
                    filtered_params[key] = value
            
            filtered_query = urlencode(filtered_params, doseq=True)
            normalized_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path.rstrip('/'),
                parsed.params,
                filtered_query,
                ''
            ))
            
            return normalized_url
            
        except Exception as e:
            logger.error(f"Error normalizing URL for deduplication {url}: {e}")
            return url.lower().strip()
    
    def is_duplicate_url(self, url: str) -> bool:
        normalized = self.normalize_url_for_deduplication(url)
        return normalized in self.visited_urls
    
    def extract_content(self, html_content: str, url: str) -> Dict[str, Any]:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            title = ""
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
            else:
                h1_tag = soup.find('h1')
                if h1_tag:
                    title = h1_tag.get_text().strip()
            
            for element in soup(["script", "style"]):
                element.decompose()
            
            obvious_nav_selectors = [
                'nav', 'header[role="banner"]', 'footer[role="contentinfo"]',
                '[role="navigation"]', '[role="banner"]', '[role="contentinfo"]',
                '.skip-link', '.skip-to-content', '#skip-link', '#skip-to-content'
            ]
            
            for selector in obvious_nav_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            body = soup.find('body')
            if body:
                content = body.get_text(separator=' ', strip=True)
            else:
                content = soup.get_text(separator=' ', strip=True)
            
            if content:
                unwanted_phrases = [
                    "Skip to main content", "Skip to content", "Jump to navigation",
                    "Contribute my reading data to research", "Help Improve arXiv",
                    "arXiv is working with academic researchers",
                    "By clicking 'I agree' below, you consent",
                    "Reading data will never be shared publicly",
                    "We gratefully acknowledge support from",
                    "the Simons Foundation, member institutions , and all contributors. Donate",
                    "cs.HC Help | open search GO open navigation menu",
                    "Login Help Pages About", "Advanced Search All fields",
                    "open search GO open navigation menu quick links",
                    "I Agree Opt Out Close", "Status Login Help",
                    "Title Author Abstract Comments Journal reference",
                    "ACM classification MSC classification Report number",
                    "arXiv identifier DOI ORCID arXiv author ID Help pages Full text Search"
                ]
                
                for phrase in unwanted_phrases:
                    content = content.replace(phrase, " ")
                
                content = ' '.join(content.split())
            
            page_id = str(uuid.uuid4())
            created_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            
            return {
                "created_at": created_at,
                "id": page_id,
                "source_url": url,
                "title": title,
                "content": content if content else "No content could be extracted"
            }
        
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return {
                "created_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "id": str(uuid.uuid4()),
                "source_url": url,
                "title": "",
                "content": f"Error extracting content: {str(e)}"
            }
    
    def scrape_page(self, url: str) -> Dict[str, Any]:
        try:
            logger.info(f"Scraping: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                logger.warning(f"Skipping non-HTML content: {url}")
                return {
                    "created_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                    "id": str(uuid.uuid4()),
                    "source_url": url,
                    "title": "Non-HTML Content",
                    "content": "Skipped non-HTML content"
                }
            
            return self.extract_content(response.text, url)
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            return {
                "created_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "id": str(uuid.uuid4()),
                "source_url": url,
                "title": "",
                "content": f"Request error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {e}")
            return {
                "created_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "id": str(uuid.uuid4()),
                "source_url": url,
                "title": "",
                "content": f"Unexpected error: {str(e)}"
            }
    
    def crawl_website(self) -> List[Dict[str, Any]]:
        scraped_data = []
        urls_to_visit = [self.normalize_url(self.base_url)]
        
        while urls_to_visit and len(scraped_data) < self.max_pages:
            current_url = urls_to_visit.pop(0)
            
            if current_url in self.visited_urls:
                continue
            
            self.visited_urls.add(current_url)
            
            page_data = self.scrape_page(current_url)
            if page_data:
                scraped_data.append(page_data)
                
                if self.callback:
                    self.callback(page_data)
                
                try:
                    response = self.session.get(current_url, timeout=self.timeout)
                    if response.status_code == 200 and 'text/html' in response.headers.get('content-type', '').lower():
                        new_links = self.extract_links(response.text, current_url)
                        
                        for link in new_links:
                            if link not in self.visited_urls and link not in urls_to_visit:
                                urls_to_visit.append(link)
                
                except Exception as e:
                    logger.error(f"Error extracting links from {current_url}: {e}")
        
        logger.info(f"Crawling completed. Scraped {len(scraped_data)} pages.")
        return scraped_data

@app.get("/")
async def root():
    return {
        "message": "Web Scraping API",
        "description": "A FastAPI-based web scraping API that crawls websites and extracts article content - Made by Eng: Amr Hossam",
        "version": "1.0.0",
        "endpoints": {
            "/scrape-single": "POST - Scrape a single page",
            "/scrape-pages": "POST - Scrape limited pages",
            "/scrape-all": "POST - Scrape all pages",
            "/scrape-stream": "POST - Stream scraping results",
            "/health": "GET - Health check",
            "/docs": "GET - API documentation"
        }
    }

@app.get("/api", tags=["System Info"])
async def api_info():
    return {
        "message": "Web Scraping API",
        "description": "Advanced web scraping API that crawls websites and extracts article content - Made by Eng: Amr Hossam",
        "endpoints": {
            "/scrape": "POST - Scrape limited number of pages",
            "/scrape-single": "POST - Scrape single page only",
            "/scrape-all": "POST - Scrape ALL pages (unlimited)",
            "/docs": "GET - Interactive API documentation",
            "/health": "GET - System health check",
            "/api": "GET - API information"
        },
        "features": [
            "Automatic link discovery",
            "Safe with duplicate prevention", 
            "Smart content extraction",
            "High performance with HTTP sessions",
            "Support for limited and unlimited scraping"
        ],
        "developer": "Eng: Amr Hossam",
        "version": "1.0.0"
    }

@app.get("/health", tags=["System Info"])
async def health_check():
    return {
        "status": "healthy",
        "service": "web-scraping-api",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }

@app.post("/scrape-single", response_model=ScrapedPage, tags=["Web Scraping"])
async def scrape_single_page(
    url: str = Query(
        ..., 
        description="The URL of the specific page to scrape", 
        examples={"example": {"summary": "Article URL", "value": "https://example.com/article"}}
    ),
    timeout: int = Query(
        10, 
        description="Request timeout in seconds for the page", 
        ge=1, 
        le=60, 
        examples={"default": {"summary": "Timeout in seconds", "value": 10}}
    )
):
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        if parsed_url.scheme not in ['http', 'https']:
            raise HTTPException(status_code=400, detail="URL must use HTTP or HTTPS protocol")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {str(e)}")
    
    try:
        scraper = WebScraper(url, timeout=timeout, max_pages=1)
        page_data = scraper.scrape_page(url)
        
        if not page_data or not page_data.get('content'):
            raise HTTPException(status_code=404, detail="No content could be extracted from the provided URL")
        
        return {"data": page_data}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during single page scraping: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/scrape-all", response_model=List[ScrapedPage], tags=["Web Scraping"])
async def scrape_all_pages(
    url: str = Query(
        ..., 
        description="The base URL of the website to scrape completely", 
        examples={"example": {"summary": "Base site URL", "value": "https://example.com"}}
    ),
    timeout: int = Query(
        10, 
        description="Request timeout in seconds for each page", 
        ge=1, 
        le=60, 
        examples={"default": {"summary": "Timeout in seconds", "value": 10}}
    )
):
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        if parsed_url.scheme not in ['http', 'https']:
            raise HTTPException(status_code=400, detail="URL must use HTTP or HTTPS protocol")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {str(e)}")
    
    try:
        scraper = WebScraper(url, timeout=timeout, max_pages=999999)
        scraped_data = scraper.crawl_website()
        
        if not scraped_data:
            raise HTTPException(status_code=404, detail="No content could be scraped from the provided URL")
        
        formatted_response = []
        for page_data in scraped_data:
            formatted_response.append({"data": page_data})
        
        return formatted_response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during unlimited scraping: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/scrape-pages", response_model=List[ScrapedPage], tags=["Web Scraping"])
async def scrape_website(
    url: str = Query(
        ..., 
        description="The base URL of the website to scrape", 
        examples={"example": {"summary": "Base site URL", "value": "https://example.com"}}
    ),
    max_pages: int = Query(
        100, 
        description="Maximum number of pages to scrape", 
        ge=1, 
        le=999999, 
        examples={"default": {"summary": "Max pages to crawl", "value": 50}}
    ),
    timeout: int = Query(
        10, 
        description="Request timeout in seconds for each page", 
        ge=1, 
        le=60, 
        examples={"default": {"summary": "Timeout in seconds", "value": 10}}
    )
):
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        if parsed_url.scheme not in ['http', 'https']:
            raise HTTPException(status_code=400, detail="URL must use HTTP or HTTPS protocol")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {str(e)}")
    
    try:
        scraper = WebScraper(url, timeout=timeout, max_pages=max_pages)
        scraped_data = scraper.crawl_website()
        
        if not scraped_data:
            raise HTTPException(status_code=404, detail="No content could be scraped from the provided URL")
        
        formatted_response = []
        for page_data in scraped_data:
            formatted_response.append({"data": page_data})
        
        return formatted_response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

class StreamRequest(BaseModel):
    url: str
    max_pages: int = 100
    timeout: int = 10

async def generate_stream(scraper: WebScraper) -> AsyncGenerator[str, None]:
    urls_to_visit = [scraper.normalize_url(scraper.base_url)]
    scraped_count = 0
    
    yield f"data: {json.dumps({'type': 'start', 'message': 'Starting scraping...'})}\n\n"
    
    while urls_to_visit and scraped_count < scraper.max_pages:
        current_url = urls_to_visit.pop(0)
        
        if current_url in scraper.visited_urls:
            continue
        
        scraper.visited_urls.add(current_url)
        page_data = scraper.scrape_page(current_url)
        
        if page_data:
            scraped_count += 1
            progress = {
                'type': 'page',
                'data': page_data,
                'progress': {
                    'current': scraped_count,
                    'total': scraper.max_pages,
                    'percentage': min(100, int((scraped_count / scraper.max_pages) * 100))
                }
            }
            yield f"data: {json.dumps(progress)}\n\n"
            
            try:
                response = scraper.session.get(current_url, timeout=scraper.timeout)
                if response.status_code == 200 and 'text/html' in response.headers.get('content-type', '').lower():
                    new_links = scraper.extract_links(response.text, current_url)
                    for link in new_links:
                        if link not in scraper.visited_urls and link not in urls_to_visit:
                            urls_to_visit.append(link)
            except Exception as e:
                logger.error(f"Error extracting links: {e}")
        
        await asyncio.sleep(0.1)
    
    yield f"data: {json.dumps({'type': 'complete', 'total': scraped_count, 'message': 'Scraping completed'})}\n\n"

@app.post("/scrape-stream", tags=["Web Scraping"])
async def scrape_stream(request: StreamRequest):
    try:
        parsed_url = urlparse(request.url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        if parsed_url.scheme not in ['http', 'https']:
            raise HTTPException(status_code=400, detail="URL must use HTTP or HTTPS protocol")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {str(e)}")
    
    scraper = WebScraper(request.url, timeout=request.timeout, max_pages=request.max_pages)
    
    return StreamingResponse(
        generate_stream(scraper),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
# الشيكو بيطس