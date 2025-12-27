# Lothian Buses Scraper Microservice
#
# A lightweight FastAPI microservice that scrapes live bus times
# from Lothian Buses as a fallback data source for Home Assistant.
#
# Features:
# - Caches responses for 90 seconds to avoid hammering the source
# - Headless browser scraping using Playwright
# - Clean JSON output compatible with Home Assistant REST sensors
# - Health check endpoint for monitoring

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, asdict
from functools import lru_cache

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from playwright.async_api import async_playwright, Browser, Page
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment
CACHE_TTL_SECONDS = int(os.getenv('CACHE_TTL_SECONDS', '90'))
REQUEST_TIMEOUT_SECONDS = int(os.getenv('REQUEST_TIMEOUT_SECONDS', '30'))
LOTHIAN_BASE_URL = os.getenv('LOTHIAN_BASE_URL', 'https://www.lothianbuses.com/live-travel-info/live-bus-times/')

app = FastAPI(
    title="Lothian Buses Scraper",
    description="Scrapes live bus times from Lothian Buses as a fallback data source",
    version="1.0.0"
)

# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------

class BusDeparture(BaseModel):
    route: str
    due_mins: int
    aimed: Optional[str] = None
    expected: Optional[str] = None
    destination: Optional[str] = None
    status: str  # "On time", "Late", "Early", "Scheduled", "Unknown"


class StopDepartures(BaseModel):
    stop_code: str
    stop_name: Optional[str] = None
    generated_at: str
    departures: list[BusDeparture]
    error: Optional[str] = None
    cached: bool = False


# -----------------------------------------------------------------------------
# Cache Implementation
# -----------------------------------------------------------------------------

@dataclass
class CacheEntry:
    data: StopDepartures
    expires_at: datetime


class SimpleCache:
    def __init__(self, ttl_seconds: int = 90):
        self._cache: dict[str, CacheEntry] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[StopDepartures]:
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if datetime.now() < entry.expires_at:
                    logger.info(f"Cache hit for {key}")
                    result = entry.data.model_copy()
                    result.cached = True
                    return result
                else:
                    logger.info(f"Cache expired for {key}")
                    del self._cache[key]
            return None
    
    async def set(self, key: str, data: StopDepartures):
        async with self._lock:
            self._cache[key] = CacheEntry(
                data=data,
                expires_at=datetime.now() + self._ttl
            )
            logger.info(f"Cache set for {key}, expires in {self._ttl.seconds}s")
    
    async def clear(self):
        async with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")


cache = SimpleCache(ttl_seconds=CACHE_TTL_SECONDS)

# -----------------------------------------------------------------------------
# Browser Management
# -----------------------------------------------------------------------------

class BrowserManager:
    def __init__(self):
        self._browser: Optional[Browser] = None
        self._playwright = None
        self._lock = asyncio.Lock()
    
    async def get_browser(self) -> Browser:
        async with self._lock:
            if self._browser is None or not self._browser.is_connected():
                logger.info("Starting new browser instance")
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process'
                    ]
                )
            return self._browser
    
    async def close(self):
        async with self._lock:
            if self._browser:
                await self._browser.close()
                self._browser = None
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            logger.info("Browser closed")


browser_manager = BrowserManager()

# -----------------------------------------------------------------------------
# Scraping Logic
# -----------------------------------------------------------------------------

async def scrape_lothian_stop(stop_code: str) -> StopDepartures:
    """
    Scrape live bus times from Lothian Buses website.
    
    The website uses a form/search interface. We need to:
    1. Navigate to the live bus times page
    2. Enter the stop code
    3. Wait for results
    4. Parse the departure information
    """
    browser = await browser_manager.get_browser()
    page = await browser.new_page()
    
    departures: list[BusDeparture] = []
    stop_name: Optional[str] = None
    error: Optional[str] = None
    
    try:
        # Set a reasonable viewport
        await page.set_viewport_size({'width': 1280, 'height': 720})
        
        # Navigate to the live bus times page
        logger.info(f"Navigating to Lothian Buses for stop {stop_code}")
        await page.goto(LOTHIAN_BASE_URL, timeout=REQUEST_TIMEOUT_SECONDS * 1000)
        
        # Wait for the page to load
        await page.wait_for_load_state('networkidle', timeout=10000)
        
        # Try to find and fill the stop search input
        # The exact selectors may need adjustment based on the actual website structure
        search_selectors = [
            'input[name="stop"]',
            'input[placeholder*="stop"]',
            'input[id*="stop"]',
            'input[type="search"]',
            '#stop-search',
            '.stop-search input',
            'input.form-control'
        ]
        
        search_input = None
        for selector in search_selectors:
            try:
                search_input = await page.wait_for_selector(selector, timeout=3000)
                if search_input:
                    logger.info(f"Found search input with selector: {selector}")
                    break
            except:
                continue
        
        if search_input:
            # Enter the stop code
            await search_input.fill(stop_code)
            await page.keyboard.press('Enter')
            
            # Wait for results to load
            await asyncio.sleep(3)
            await page.wait_for_load_state('networkidle', timeout=15000)
        else:
            # Try direct URL with stop code
            direct_url = f"{LOTHIAN_BASE_URL}?stop={stop_code}"
            logger.info(f"Trying direct URL: {direct_url}")
            await page.goto(direct_url, timeout=REQUEST_TIMEOUT_SECONDS * 1000)
            await page.wait_for_load_state('networkidle', timeout=15000)
        
        # Try to extract stop name
        stop_name_selectors = [
            '.stop-name',
            'h1.stop-title',
            'h2.stop-name',
            '.departure-board-header h2',
            '[data-stop-name]'
        ]
        
        for selector in stop_name_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    stop_name = await elem.text_content()
                    stop_name = stop_name.strip() if stop_name else None
                    if stop_name:
                        break
            except:
                continue
        
        # Extract departure information
        # Common patterns for departure boards
        departure_selectors = [
            '.departure-row',
            '.bus-departure',
            'tr.departure',
            '.live-times li',
            '.departure-board tbody tr',
            '[data-departure]'
        ]
        
        departure_elements = []
        for selector in departure_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements and len(elements) > 0:
                    departure_elements = elements
                    logger.info(f"Found {len(elements)} departures with selector: {selector}")
                    break
            except:
                continue
        
        for elem in departure_elements[:10]:  # Limit to first 10 departures
            try:
                # Try to extract route number
                route = None
                route_selectors = ['.route', '.service', '.bus-number', 'td:first-child', '.line-number']
                for sel in route_selectors:
                    try:
                        route_elem = await elem.query_selector(sel)
                        if route_elem:
                            route = await route_elem.text_content()
                            route = route.strip() if route else None
                            if route:
                                break
                    except:
                        continue
                
                if not route:
                    continue
                
                # Try to extract time/minutes
                due_mins = 0
                time_selectors = ['.time', '.due', '.minutes', 'td:last-child', '.departure-time']
                time_text = None
                for sel in time_selectors:
                    try:
                        time_elem = await elem.query_selector(sel)
                        if time_elem:
                            time_text = await time_elem.text_content()
                            time_text = time_text.strip() if time_text else None
                            if time_text:
                                break
                    except:
                        continue
                
                if time_text:
                    # Parse time text - could be "5 min", "Due", "08:45", etc.
                    time_text_lower = time_text.lower()
                    if 'due' in time_text_lower or 'now' in time_text_lower:
                        due_mins = 0
                    elif 'min' in time_text_lower:
                        # Extract number from "5 min" or "5 mins"
                        import re
                        match = re.search(r'(\d+)', time_text)
                        if match:
                            due_mins = int(match.group(1))
                    elif ':' in time_text:
                        # It's a clock time like "08:45"
                        try:
                            time_parts = time_text.split(':')
                            hour = int(time_parts[0])
                            minute = int(time_parts[1][:2])  # Handle "08:45am" etc.
                            now = datetime.now()
                            dep_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                            if dep_time < now:
                                dep_time += timedelta(days=1)
                            due_mins = int((dep_time - now).total_seconds() / 60)
                        except:
                            pass
                
                # Try to extract destination
                destination = None
                dest_selectors = ['.destination', '.to', 'td:nth-child(2)']
                for sel in dest_selectors:
                    try:
                        dest_elem = await elem.query_selector(sel)
                        if dest_elem:
                            destination = await dest_elem.text_content()
                            destination = destination.strip() if destination else None
                            if destination:
                                break
                    except:
                        continue
                
                # Determine status
                status = "Scheduled"  # Default
                status_selectors = ['.status', '.delay', '[data-status]']
                for sel in status_selectors:
                    try:
                        status_elem = await elem.query_selector(sel)
                        if status_elem:
                            status_text = await status_elem.text_content()
                            if status_text:
                                status_text = status_text.strip().lower()
                                if 'late' in status_text or 'delayed' in status_text:
                                    status = "Late"
                                elif 'early' in status_text:
                                    status = "Early"
                                elif 'on time' in status_text:
                                    status = "On time"
                            break
                    except:
                        continue
                
                departures.append(BusDeparture(
                    route=route,
                    due_mins=due_mins,
                    aimed=time_text,
                    expected=time_text,
                    destination=destination,
                    status=status
                ))
                
            except Exception as e:
                logger.warning(f"Error parsing departure element: {e}")
                continue
        
        # If no departures found, try alternative parsing
        if not departures:
            logger.warning("No departures found with standard selectors, trying page text extraction")
            page_text = await page.content()
            
            # Log a snippet for debugging
            logger.debug(f"Page content snippet: {page_text[:2000]}")
            
            error = "No departure data found - website structure may have changed"
    
    except asyncio.TimeoutError:
        error = f"Timeout while fetching stop {stop_code}"
        logger.error(error)
    except Exception as e:
        error = f"Error scraping stop {stop_code}: {str(e)}"
        logger.error(error)
    finally:
        await page.close()
    
    return StopDepartures(
        stop_code=stop_code,
        stop_name=stop_name,
        generated_at=datetime.now().isoformat(),
        departures=departures,
        error=error,
        cached=False
    )


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Lothian Buses Scraper",
        "version": "1.0.0",
        "endpoints": {
            "/lothian/stop/{stop_code}": "Get live departures for a stop",
            "/health": "Health check",
            "/cache/clear": "Clear the cache"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_ttl_seconds": CACHE_TTL_SECONDS
    }


@app.get("/lothian/stop/{stop_code}", response_model=StopDepartures)
async def get_stop_departures(stop_code: str):
    """
    Get live bus departures for a specific stop.
    
    Args:
        stop_code: The NaPTAN/ATCO stop code or stop name/number
    
    Returns:
        StopDepartures object with departure information
    """
    # Normalize stop code
    stop_code = stop_code.strip().upper()
    
    if not stop_code:
        raise HTTPException(status_code=400, detail="Stop code is required")
    
    # Check cache first
    cached_data = await cache.get(stop_code)
    if cached_data:
        return cached_data
    
    # Scrape fresh data
    logger.info(f"Fetching fresh data for stop {stop_code}")
    data = await scrape_lothian_stop(stop_code)
    
    # Cache the result (even if error, to prevent hammering)
    await cache.set(stop_code, data)
    
    return data


@app.post("/cache/clear")
async def clear_cache():
    """Clear the cache."""
    await cache.clear()
    return {"status": "cache cleared", "timestamp": datetime.now().isoformat()}


# -----------------------------------------------------------------------------
# Lifecycle Events
# -----------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    """Initialize browser on startup."""
    logger.info("Starting Lothian Buses Scraper service")
    # Pre-warm the browser
    try:
        await browser_manager.get_browser()
        logger.info("Browser pre-warmed successfully")
    except Exception as e:
        logger.warning(f"Browser pre-warm failed (will retry on first request): {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up browser on shutdown."""
    logger.info("Shutting down Lothian Buses Scraper service")
    await browser_manager.close()


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv('PORT', '8765'))
    host = os.getenv('HOST', '0.0.0.0')
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=os.getenv('DEBUG', 'false').lower() == 'true',
        log_level="info"
    )
