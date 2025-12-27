# Scraper Microservice - Local Development

## Quick Start

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run the server
python app.py
```

## Testing

```bash
# Health check
curl http://localhost:8765/health

# Get departures (replace with actual stop code)
curl http://localhost:8765/lothian/stop/6200206710

# Clear cache
curl -X POST http://localhost:8765/cache/clear
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8765` | Server port |
| `HOST` | `0.0.0.0` | Server host |
| `CACHE_TTL_SECONDS` | `90` | Cache duration |
| `REQUEST_TIMEOUT_SECONDS` | `30` | Browser timeout |
| `DEBUG` | `false` | Enable debug mode |

## Docker

```bash
# Build image
docker build -t lothian-scraper .

# Run container
docker run -d -p 8765:8765 --name lothian-scraper lothian-scraper

# View logs
docker logs -f lothian-scraper

# Stop
docker stop lothian-scraper && docker rm lothian-scraper
```
