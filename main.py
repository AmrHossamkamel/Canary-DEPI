from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Dict, Any, Set, Generator, AsyncGenerator
import requests
from bs4 import BeautifulSoup
import uuid
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
import logging
from pydantic import BaseModel
import uvicorn
import os
import json
import asyncio
import trafilatura

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Web Scraping API",
    description="A FastAPI-based web scraping API that crawls websites and extracts article content - Made by Eng: Amr Hossam",
    version="1.0.0"
)

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

class ScrapedPage(BaseModel):
    """Model for scraped page data"""
    data: Dict[str, Any]

class WebScraper:
    def __init__(self, base_url: str, timeout: int = 10, max_pages: int = 100, callback=None):
        self.base_url = base_url
        self.timeout = timeout
        self.max_pages = max_pages
        self.visited_urls: Set[str] = set()
        self.session = requests.Session()
        self.callback = callback  # Callback function for streaming results
        
        # Set user agent to avoid blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Parse base URL to get domain
        parsed_url = urlparse(base_url)
        self.domain = parsed_url.netloc
        self.scheme = parsed_url.scheme
    
    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain"""
        try:
            parsed = urlparse(url)
            return parsed.netloc == self.domain or parsed.netloc == f"www.{self.domain}" or parsed.netloc == self.domain.replace("www.", "")
        except Exception:
            return False
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and sorting query parameters"""
        try:
            parsed = urlparse(url)
            # Remove fragment and normalize
            normalized = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path.rstrip('/') if parsed.path != '/' else parsed.path,
                parsed.params,
                parsed.query,
                ''  # Remove fragment
            ))
            return normalized
        except Exception:
            return url
    
    def extract_links(self, html_content: str, base_url: str) -> Set[str]:
        """Extract all internal links from HTML content"""
        links = set()
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all anchor tags with href attributes
            for link in soup.find_all('a', href=True):
                href_attr = link.get('href')
                if not href_attr:
                    continue
                href = str(href_attr).strip()
                if not href or href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
                    continue
                
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                
                # Check if it's the same domain and not duplicate
                if self.is_same_domain(absolute_url) and not self.is_duplicate_url(absolute_url):
                    normalized_url = self.normalize_url(absolute_url)
                    links.add(normalized_url)
        
        except Exception as e:
            logger.error(f"Error extracting links: {e}")
        
        return links
    
    def normalize_url_for_deduplication(self, url: str) -> str:
        """Enhanced URL normalization for better duplicate detection"""
        try:
            parsed = urlparse(url.lower().strip())
            
            # Remove common tracking parameters
            query_params = parse_qs(parsed.query)
            filtered_params = {}
            
            # Keep only meaningful parameters, filter out tracking
            tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 
                             'fbclid', 'gclid', 'ref', 'source', '_ga', '_gl', 'mc_cid', 'mc_eid',
                             'campaign', 'medium', 'content', 'term', 'msclkid', 'wbraid', 'gbraid'}
            
            for key, value in query_params.items():
                if key.lower() not in tracking_params:
                    filtered_params[key] = value
            
            # Rebuild URL without tracking parameters
            filtered_query = urlencode(filtered_params, doseq=True)
            normalized_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path.rstrip('/'),  # Remove trailing slash
                parsed.params,
                filtered_query,
                ''  # Remove fragment
            ))
            
            return normalized_url
            
        except Exception as e:
            logger.error(f"Error normalizing URL for deduplication {url}: {e}")
            return url.lower().strip()
    
    def is_duplicate_url(self, url: str) -> bool:
        """Check if URL is duplicate using enhanced normalization"""
        normalized = self.normalize_url_for_deduplication(url)
        return normalized in self.visited_urls
    
    def extract_content(self, html_content: str, url: str) -> Dict[str, Any]:
        """Extract title and content from HTML - keeps all content but removes only unwanted navigation elements"""
        try:
            # Use BeautifulSoup for content extraction
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title = ""
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
            else:
                h1_tag = soup.find('h1')
                if h1_tag:
                    title = h1_tag.get_text().strip()
            
            # Remove only script, style, and obvious navigation/menu elements
            # Keep everything else to ensure we don't miss any content
            for element in soup(["script", "style"]):
                element.decompose()
            
            # Remove only very obvious navigation elements (not aggressive)
            obvious_nav_selectors = [
                'nav', 'header[role="banner"]', 'footer[role="contentinfo"]',
                '[role="navigation"]', '[role="banner"]', '[role="contentinfo"]',
                '.skip-link', '.skip-to-content', '#skip-link', '#skip-to-content'
            ]
            
            for selector in obvious_nav_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            # Extract complete page content from body
            body = soup.find('body')
            if body:
                content = body.get_text(separator=' ', strip=True)
            else:
                content = soup.get_text(separator=' ', strip=True)
            
            # Clean up content - remove only specific unwanted phrases but keep everything else
            if content:
                # Remove common navigation phrases that don't contain valuable content
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
                
                # Clean up extra whitespace
                content = ' '.join(content.split())
            
            # Generate unique ID and timestamp
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
        """Scrape a single page and return extracted data"""
        try:
            logger.info(f"Scraping: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Check if content type is HTML
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
        """Crawl the entire website and return scraped data"""
        scraped_data = []
        urls_to_visit = [self.normalize_url(self.base_url)]
        
        while urls_to_visit and len(scraped_data) < self.max_pages:
            current_url = urls_to_visit.pop(0)
            
            # Skip if already visited
            if current_url in self.visited_urls:
                continue
            
            # Mark as visited
            self.visited_urls.add(current_url)
            
            # Scrape the page
            page_data = self.scrape_page(current_url)
            if page_data:
                scraped_data.append(page_data)
                
                # Call callback if streaming is enabled
                if self.callback:
                    self.callback(page_data)
                
                # Extract links only if we successfully scraped the page
                try:
                    response = self.session.get(current_url, timeout=self.timeout)
                    if response.status_code == 200 and 'text/html' in response.headers.get('content-type', '').lower():
                        new_links = self.extract_links(response.text, current_url)
                        
                        # Add new links to visit queue
                        for link in new_links:
                            if link not in self.visited_urls and link not in urls_to_visit:
                                urls_to_visit.append(link)
                
                except Exception as e:
                    logger.error(f"Error extracting links from {current_url}: {e}")
        
        logger.info(f"Crawling completed. Scraped {len(scraped_data)} pages.")
        return scraped_data

@app.get("/")
async def root():
    """Serve the main UI"""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    else:
        # Fallback API information if static files don't exist
        return {
            "message": "Web Scraping API",
            "description": "A FastAPI-based web scraping API that crawls websites and extracts article content - Made by Eng: Amr Hossam",
            "endpoints": {
                "/scrape": "POST - Scrape a website for article content",
                "/docs": "GET - API documentation"
            }
        }

@app.get("/api", tags=["System Info"])
async def api_info():
    """API endpoint information and available routes"""
    return {
        "message": "🕷️ Web Scraping API",
        "description": "Advanced web scraping API that crawls websites and extracts article content - Made by Eng: Amr Hossam",
        "endpoints": {
            "/scrape": "🔍 POST - Scrape limited number of pages",
            "/scrape-single": "🎯 POST - Scrape single page only",
            "/scrape-all": "🚀 POST - Scrape ALL pages (unlimited)",
            "/docs": "📚 GET - Interactive API documentation",
            "/health": "💚 GET - System health check",
            "/api": "📊 GET - API information"
        },
        "features": [
            "🕸️ Automatic link discovery",
            "🛡️ Safe with duplicate prevention", 
            "📊 Smart content extraction",
            "⚡ High performance with HTTP sessions",
            "🎯 Support for limited and unlimited scraping"
        ],
        "developer": "👨‍💻 Eng: Amr Hossam",
        "version": "1.0.0"
    }

@app.post("/scrape-single", response_model=ScrapedPage, tags=["Web Scraping"])
async def scrape_single_page(
    url: str = Query(
        ..., 
        description="The URL of the specific page to scrape",
        example="https://example.com/article"
    ),
    timeout: int = Query(
        10, 
        description="Request timeout in seconds for the page", 
        ge=1, 
        le=60,
        example=10
    )
):
    """
    **Extract content from a single page only**
    
    This endpoint scrapes only the specified page without following any links.
    Perfect for extracting content from a specific article or page.
    
    ## Features:
    - 🎯 **Single Page**: Only scrapes the exact URL provided
    - ⚡ **Fast**: No link discovery, direct page scraping
    - 📊 **Smart Extraction**: Same content extraction as full scraping
    - 🛡️ **Safe**: No risk of infinite crawling
    
    ## Parameters:
    - **url**: Exact URL of the page to scrape
    - **timeout**: Timeout in seconds for the request
    
    ## Returns:
    A single scraped page containing:
    - Title and content
    - Source URL
    - Extraction timestamp
    - Unique ID
    
    ## Usage:
    Perfect for scraping specific articles, blog posts, or individual pages
    when you don't need the entire website.
    """
    
    # Validate URL
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        if parsed_url.scheme not in ['http', 'https']:
            raise HTTPException(status_code=400, detail="URL must use HTTP or HTTPS protocol")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {str(e)}")
    
    try:
        # Initialize scraper just to use its scrape_page method
        scraper = WebScraper(url, timeout=timeout, max_pages=1)
        
        # Scrape only the single page
        page_data = scraper.scrape_page(url)
        
        if not page_data or not page_data.get('content'):
            raise HTTPException(status_code=404, detail="No content could be extracted from the provided URL")
        
        # Format response according to specified structure
        return {
            "data": page_data
        }
    
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
        example="https://example.com"
    ),
    timeout: int = Query(
        10, 
        description="Request timeout in seconds for each page", 
        ge=1, 
        le=60,
        example=10
    )
):
    """
    **Extract content from ALL pages on a website with no limit**
    
    This endpoint scrapes the entire website by following all internal links
    without any page limit. Perfect for complete website content extraction.
    
    ## Features:
    - 🕸️ **Complete Discovery**: Finds and scrapes every internal page
    - ♾️ **No Limits**: Continues until all pages are discovered
    - 🛡️ **Domain Safe**: Only follows links within the same domain
    - 📊 **Smart Extraction**: Same content extraction as other endpoints
    - 🔄 **Duplicate Prevention**: Avoids visiting the same page twice
    
    ## Parameters:
    - **url**: Base URL of the website to scrape completely
    - **timeout**: Timeout in seconds for each page request
    
    ## Returns:
    A list of ALL scraped pages from the website, each containing:
    - Title and content
    - Source URL
    - Extraction timestamp
    - Unique ID
    
    ## Warning:
    This may take a very long time for large websites and will scrape
    every discoverable page. Use with caution on very large sites.
    """
    
    # Validate URL
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        if parsed_url.scheme not in ['http', 'https']:
            raise HTTPException(status_code=400, detail="URL must use HTTP or HTTPS protocol")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {str(e)}")
    
    try:
        # Initialize scraper with very high max_pages for unlimited scraping
        scraper = WebScraper(url, timeout=timeout, max_pages=999999)
        
        # Crawl entire website
        scraped_data = scraper.crawl_website()
        
        if not scraped_data:
            raise HTTPException(status_code=404, detail="No content could be scraped from the provided URL")
        
        # Format response according to specified structure
        formatted_response = []
        for page_data in scraped_data:
            formatted_response.append({
                "data": page_data
            })
        
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
        example="https://example.com"
    ),
    max_pages: int = Query(
        100, 
        description="Maximum number of pages to scrape. Use 999999 or higher for unlimited scraping", 
        ge=1, 
        le=999999,
        example=50
    ),
    timeout: int = Query(
        10, 
        description="Request timeout in seconds for each page", 
        ge=1, 
        le=60,
        example=10
    )
):
    """
    **Extract content from websites**
    
    This API visits the specified website and extracts content from all internal pages.
    
    ## Features:
    - 🕸️ **Auto Discovery**: Follows all internal links automatically
    - 🛡️ **Safe**: Stays within the specified domain only
    - 📊 **Smart Extraction**: Cleans content and extracts titles and text
    - ⚡ **Fast**: Uses persistent HTTP sessions for performance
    - 🔄 **Duplicate Prevention**: Avoids visiting the same page twice
    
    ## Parameters:
    - **url**: Base URL of the website (must start with http or https)
    - **max_pages**: Maximum number of pages to scrape (use 999999+ for unlimited)
    - **timeout**: Timeout in seconds for each page request
    
    ## Returns:
    A list of scraped pages, each containing:
    - Title and content
    - Source URL
    - Extraction timestamp
    - Unique ID
    
    ## Usage Examples:
    - **Limited scraping**: `max_pages=50` to scrape only 50 pages
    - **Unlimited scraping**: `max_pages=999999` to scrape all pages on the website
    """
    
    # Validate URL
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        if parsed_url.scheme not in ['http', 'https']:
            raise HTTPException(status_code=400, detail="URL must use HTTP or HTTPS protocol")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {str(e)}")
    
    try:
        # Initialize scraper
        scraper = WebScraper(url, timeout=timeout, max_pages=max_pages)
        
        # Crawl website
        scraped_data = scraper.crawl_website()
        
        if not scraped_data:
            raise HTTPException(status_code=404, detail="No content could be scraped from the provided URL")
        
        # Format response according to specified structure
        formatted_response = []
        for page_data in scraped_data:
            formatted_response.append({
                "data": page_data
            })
        
        return formatted_response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/scrape-stream", 
        tags=["📡 Real-time Streaming"], 
        summary="Stream scraped pages in real-time",
        description="""
## Real-time Streaming Web Scraper

Stream scraped pages in real-time with immediate results.
Each page is sent as soon as it's processed, providing live updates.

### Features:
- **📡 Real-time Streaming**: Results appear as soon as each page is scraped
- **🚀 No Waiting**: See pages immediately instead of waiting for completion  
- **📊 Live Progress**: Track scraping progress in real-time
- **🛡️ Same Security**: All security features of regular scraping
- **🎯 Limited Pages**: Control the number of pages to extract

### Usage:
Perfect for interactive applications where users want to see results immediately.
Returns streaming JSON responses with real-time updates.

### Request Body:
```json
{
    "url": "https://example.com",
    "max_pages": 50,
    "timeout": 10
}
```
        """)
async def scrape_website_stream(request: dict):
    
    # Extract parameters from request
    url = request.get('url')
    max_pages = request.get('max_pages', 50)
    timeout = request.get('timeout', 10)
    
    # Validate parameters
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    # Validate URL
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        if parsed_url.scheme not in ['http', 'https']:
            raise HTTPException(status_code=400, detail="URL must use HTTP or HTTPS protocol")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {str(e)}")
    
    async def generate_stream() -> Generator[str, None, None]:
        """Generate SSE stream for real-time scraping results"""
        scraped_count = 0
        
        def stream_callback(page_data):
            nonlocal scraped_count
            scraped_count += 1
            
            # Format the page data for streaming
            event_data = {
                "type": "page",
                "data": page_data,
                "progress": {
                    "current": scraped_count,
                    "total": max_pages,
                    "percentage": min(100, (scraped_count / max_pages) * 100)
                }
            }
            
            return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
        
        try:
            # Send start event
            start_event = {
                "type": "start",
                "message": "بدء عملية السكرابنج...",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            yield f"data: {json.dumps(start_event, ensure_ascii=False)}\n\n"
            
            # Initialize scraper with callback for streaming
            scraper = WebScraper(url, timeout=timeout, max_pages=max_pages)
            
            # Store streamed results
            streamed_results = []
            
            def capture_result(page_data):
                streamed_results.append(page_data)
                # Generate stream event
                return stream_callback(page_data)
            
            scraper.callback = capture_result
            
            # Start crawling and stream results
            urls_to_visit = [scraper.normalize_url(scraper.base_url)]
            
            while urls_to_visit and len(streamed_results) < max_pages:
                current_url = urls_to_visit.pop(0)
                
                # Skip if already visited
                if current_url in scraper.visited_urls:
                    continue
                
                # Mark as visited
                scraper.visited_urls.add(current_url)
                
                # Scrape the page
                page_data = scraper.scrape_page(current_url)
                if page_data:
                    streamed_results.append(page_data)
                    
                    # Stream the result immediately
                    event_data = {
                        "type": "page",
                        "data": page_data,
                        "progress": {
                            "current": len(streamed_results),
                            "total": max_pages,
                            "percentage": min(100, (len(streamed_results) / max_pages) * 100)
                        }
                    }
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    
                    # Extract links for next pages
                    try:
                        response = scraper.session.get(current_url, timeout=timeout)
                        if response.status_code == 200 and 'text/html' in response.headers.get('content-type', '').lower():
                            new_links = scraper.extract_links(response.text, current_url)
                            
                            # Add new links to visit queue
                            for link in new_links:
                                if link not in scraper.visited_urls and link not in urls_to_visit:
                                    urls_to_visit.append(link)
                    
                    except Exception as e:
                        logger.error(f"Error extracting links from {current_url}: {e}")
                
                # Small delay to prevent overwhelming the client and reduce duplicate processing
                await asyncio.sleep(0.2)
            
            # Send completion event
            complete_event = {
                "type": "complete",
                "message": f"تم الانتهاء! تم سكرابنج {len(streamed_results)} صفحة",
                "total_pages": len(streamed_results),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            yield f"data: {json.dumps(complete_event, ensure_ascii=False)}\n\n"
        
        except Exception as e:
            logger.error(f"Error during streaming scrape: {e}")
            error_event = {
                "type": "error",
                "message": f"حدث خطأ: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )

@app.post("/scrape-stream-unlimited", 
        tags=["🚀 Unlimited Streaming"], 
        summary="Stream unlimited website scraping",
        description="""
## Unlimited Website Scraper with Real-time Streaming

This endpoint scrapes entire websites without page limits. 
Results are streamed in real-time with immediate updates.

### Features:
- **🌐 Complete Coverage**: Continues until all discoverable pages are scraped
- **📡 Real-time Stream**: Results appear as soon as each page is processed  
- **🛡️ Advanced Protection**: Smart duplicate prevention and infinite loop protection
- **⚡ High Performance**: Uses HTTP sessions and network optimizations
- **🔍 Smart Discovery**: Automatically follows internal links

### Warning:
⚠️ **Caution**: May take a very long time for large websites and consume significant resources

### Usage:
Perfect for websites where you need comprehensive content extraction.
Returns streaming JSON responses with real-time updates.

### Request Body:
```json
{
    "url": "https://example.com",
    "timeout": 10
}
```
        """)
async def scrape_stream_unlimited(request: dict):
    
    # Extract parameters from request
    url = request.get('url')
    timeout = request.get('timeout', 10)
    
    # Validate parameters
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    # Validate URL
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        if parsed_url.scheme not in ['http', 'https']:
            raise HTTPException(status_code=400, detail="URL must use HTTP or HTTPS protocol")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {str(e)}")
    
    async def generate_unlimited_stream() -> Generator[str, None, None]:
        """Generate SSE stream for unlimited real-time scraping results"""
        scraped_count = 0
        
        try:
            # Send start event
            start_event = {
                "type": "start",
                "message": "بدء عملية السكرابنج الشامل للموقع...",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            yield f"data: {json.dumps(start_event, ensure_ascii=False)}\n\n"
            
            # Initialize scraper without page limit
            scraper = WebScraper(url, timeout=timeout, max_pages=999999)
            
            # Store streamed results
            streamed_results = []
            
            # Start crawling and stream results
            urls_to_visit = [scraper.normalize_url(scraper.base_url)]
            
            while urls_to_visit:
                current_url = urls_to_visit.pop(0)
                
                # Skip if already visited (with enhanced duplicate detection)
                normalized_for_check = scraper.normalize_url_for_deduplication(current_url)
                if normalized_for_check in scraper.visited_urls:
                    continue
                
                # Mark as visited (using enhanced normalization)
                scraper.visited_urls.add(normalized_for_check)
                
                # Scrape the page
                page_data = scraper.scrape_page(current_url)
                if page_data:
                    scraped_count += 1
                    streamed_results.append(page_data)
                    
                    # Stream the result immediately
                    event_data = {
                        "type": "page",
                        "data": page_data,
                        "progress": {
                            "current": scraped_count,
                            "total": "غير محدود",
                            "percentage": None,
                            "queue_size": len(urls_to_visit)
                        }
                    }
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    
                    # Extract links for next pages
                    try:
                        response = scraper.session.get(current_url, timeout=timeout)
                        if response.status_code == 200 and 'text/html' in response.headers.get('content-type', '').lower():
                            new_links = scraper.extract_links(response.text, current_url)
                            
                            # Add new links to visit queue
                            for link in new_links:
                                if link not in scraper.visited_urls and link not in urls_to_visit:
                                    urls_to_visit.append(link)
                    
                    except Exception as e:
                        logger.error(f"Error extracting links from {current_url}: {e}")
                
                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.2)
                
                # Enhanced URL validation to prevent duplicates and improve efficiency
                if scraped_count > 0 and scraped_count % 1000 == 0:
                    progress_event = {
                        "type": "progress",
                        "message": f"تم استخراج {scraped_count} صفحة... استمرار العمل",
                        "current": scraped_count,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    yield f"data: {json.dumps(progress_event, ensure_ascii=False)}\n\n"
            
            # Send completion event
            complete_event = {
                "type": "complete",
                "message": f"تم الانتهاء من السكرابنج الشامل! تم سكرابنج {scraped_count} صفحة",
                "total_pages": scraped_count,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            yield f"data: {json.dumps(complete_event, ensure_ascii=False)}\n\n"
        
        except Exception as e:
            logger.error(f"Error during unlimited streaming scrape: {e}")
            error_event = {
                "type": "error",
                "message": f"حدث خطأ: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_unlimited_stream(),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )

@app.get("/database")
async def database_page():
    """Serve the database management UI"""
    if os.path.exists("static/database.html"):
        return FileResponse("static/database.html")
    else:
        raise HTTPException(status_code=404, detail="Database management page not found")

@app.get("/health", tags=["System Info"])
async def health_check():
    """💚 System health check and API readiness verification"""
    return {
        "status": "healthy",
        "message": "✅ System is running normally",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": "Available 24/7",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=5000,
        reload=True,
        log_level="info"
    )
