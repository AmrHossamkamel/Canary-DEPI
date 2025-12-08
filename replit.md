# Web Scraping API

## Overview

This project is a FastAPI-based web scraping service that crawls websites and extracts article content. The application provides REST API endpoints for initiating web scraping operations on specified domains with built-in safety controls and rate limiting. It features a modern, Arabic-supporting web interface for managing scraping operations and includes comprehensive security measures to prevent abuse.

## User Preferences

Preferred communication style: Simple, everyday language (Arabic preferred).

## Recent Changes

### December 3, 2025
- **Major Architecture Refactor**: Split application into separate Frontend and Backend services
- Created `backend/` directory with API-only FastAPI server
- Created `frontend/` directory with static files served via Nginx
- Added CORS support for cross-origin requests between frontend and backend
- Created separate Dockerfiles for both services:
  - `backend/Dockerfile`: Python 3.11-slim based container for API
  - `frontend/Dockerfile`: Nginx-alpine based container for static files
- Created `docker-compose.yml` for orchestrating both services
- Frontend now uses configurable `BACKEND_API_URL` via `config.js`
- Backend listens on port 8000, Frontend serves on port 80 (mapped to 3000 in docker-compose)

### September 19, 2025
- Successfully imported GitHub project to Replit environment
- Created UV virtual environment (.venv) for dependency management
- Installed all required dependencies using UV package manager
- Configured FastAPI server workflow to run on port 5000 with proper host binding (0.0.0.0)
- Set up deployment configuration for autoscale production deployment
- Verified frontend and backend integration working correctly
- All API endpoints functioning properly with Arabic-RTL interface

### August 13, 2025
- Successfully completed migration from Replit Agent to Replit environment
- Fixed uvicorn dependency and import issues for seamless operation
- Enhanced Swagger documentation for all endpoints with professional English descriptions
- Renamed main scrape endpoint from `/scrape` to `/scrape-pages` for better clarity
- Converted streaming endpoints from GET to POST method per user request
- Updated JavaScript to use fetch with streaming readers instead of EventSource for POST compatibility
- Improved streaming endpoint documentation with clear request body examples
- Fixed JavaScript duplicate handling for unlimited streaming mode
- All streaming endpoints now use POST method with JSON request bodies
- All security features and duplicate detection systems working properly

### August 11, 2025
- Successfully migrated project from Replit Agent to Replit environment
- Fixed uvicorn dependency issue and FastAPI server configuration
- Added real-time streaming functionality using Server-Sent Events (SSE)
- Implemented /scrape-stream endpoint for live result updates
- Enhanced frontend with streaming support and real-time progress display
- Fixed EventSource method compatibility (GET instead of POST)
- User requested live streaming of scraping results instead of waiting for completion
- User feedback: Keep same deduplication system but show pages as they complete
- Maintained existing duplicate prevention while adding real-time display
- Enhanced content extraction using trafilatura library for better WordPress and modern website support
- Improved extraction for sites with dynamic content loading and Elementor-based layouts
- Added unlimited streaming endpoint (/scrape-stream-unlimited) for comprehensive website crawling
- User requested: Create unlimited streaming endpoint that continues until all website pages are scraped
- Removed safety limit per user request, added enhanced URL deduplication instead
- Enhanced URL normalization to filter tracking parameters and prevent duplicate scraping
- User feedback: Remove limits for unlimited streaming, focus on better duplicate detection

## System Architecture

### Microservices Architecture (Docker)
The application is now split into two separate services for containerized deployment:

**Backend Service** (`backend/`):
- Located at: `backend/app/main.py`
- Dockerfile: `backend/Dockerfile`
- Port: 8000
- API-only FastAPI server with CORS middleware
- Environment variable: `ALLOWED_ORIGINS` for CORS configuration

**Frontend Service** (`frontend/`):
- Located at: `frontend/public/`
- Dockerfile: `frontend/Dockerfile`
- Port: 80 (mapped to 3000 in docker-compose)
- Static files served via Nginx
- Configurable backend URL via `config.js`

**Orchestration**:
- `docker-compose.yml` manages both services
- Services communicate over Docker network `scraping-network`

### Backend Architecture
- **Framework**: FastAPI for REST API development with automatic OpenAPI documentation
- **Language**: Python 3.x with type hints and modern async/await patterns
- **HTTP Client**: Requests library with session management for connection pooling and persistent connections
- **HTML Parsing**: BeautifulSoup4 for robust content extraction and DOM manipulation
- **Data Models**: Pydantic models for request/response validation, serialization, and automatic schema generation
- **CORS**: Configurable cross-origin resource sharing for frontend separation

### Core Design Patterns
- **Object-Oriented Design**: WebScraper class encapsulates scraping logic, state management, and configuration
- **Session Management**: Persistent HTTP sessions for improved performance and connection reuse across requests
- **Rate Limiting**: Built-in timeout controls and maximum page limits to prevent resource abuse and infinite crawling
- **Domain Validation**: URL parsing and domain matching to ensure scraping operations stay within specified boundaries
- **State Tracking**: Visited URL tracking with sets to prevent duplicate requests and infinite loops

### Security & Safety Features
- **User Agent Spoofing**: Mimics legitimate browser headers to avoid bot detection and access restrictions
- **Domain Restriction**: Enforces same-domain crawling to prevent unauthorized cross-domain scraping
- **Request Limits**: Configurable maximum page limits and timeout controls to prevent server overload
- **URL Deduplication**: Comprehensive visited URL tracking to prevent infinite loops and duplicate processing
- **Input Validation**: Pydantic model validation for all API inputs and outputs

### Frontend Architecture
- **Modern UI**: Responsive Arabic-RTL supporting interface with 3D styling and animations
- **Real-time Status**: Live API health monitoring and operation status updates
- **Form Validation**: Client-side input validation with real-time feedback
- **Results Management**: Download functionality and result visualization with clear/export options
- **Progressive Enhancement**: Works without JavaScript but enhanced experience with it enabled

### Data Processing
- **Content Extraction**: Advanced HTML parsing with BeautifulSoup for clean content extraction
- **URL Normalization**: Proper URL joining, parsing, and canonicalization for link following
- **Structured Output**: Consistent JSON responses with Pydantic model validation
- **Error Handling**: Comprehensive exception handling with meaningful error messages

## External Dependencies

### Core Backend Libraries
- **FastAPI**: Modern web framework for building REST APIs with automatic documentation
- **Requests**: HTTP library for making web requests with session management
- **BeautifulSoup4**: HTML/XML parsing library for content extraction
- **Pydantic**: Data validation and serialization using Python type annotations
- **Uvicorn**: Lightning-fast ASGI server for running FastAPI applications

### Frontend Dependencies
- **Google Fonts**: Cairo font family for Arabic text support
- **Modern CSS**: CSS Grid, Flexbox, and CSS custom properties for responsive design
- **Vanilla JavaScript**: No framework dependencies, pure JavaScript for API interaction

### Python Standard Library
- **urllib.parse**: URL parsing, joining, and manipulation utilities
- **datetime**: Timestamp generation and timezone handling for request tracking
- **logging**: Structured logging for debugging and monitoring
- **uuid**: Unique identifier generation for request tracking
- **os**: File system operations for static file serving