# Stock Tracker Agent


- [ ] TODO: add tracker for individual people/politicians, what are they trading?
- [ ] TODO: add tracker/researcher for crypto values
- [ ] TODO: add speculator for cheap stocks (for fun)


An AI-powered agent that tracks selected stock prices, analyzes market news when significant price changes occur, and keeps you informed via automated Telegram messages. You can also interact with the agent by sending Telegram messages to add or remove stocks from your tracker list.

---

## 🎯 Use Case

- **Monitor** stocks for significant price movements (>1% change)
- **Receive** concise market news summaries when price changes are detected
- **Get** instant Telegram alerts for actionable events
- **Control** your tracker list by sending Telegram commands (add/remove stocks)

---

## 🚀 Features

- Automated stock tracking and alerting
- Market news analysis using AI
- Telegram bot notifications and interaction
- Interactive commands to manage your tracker list
- FastAPI web service for deployment
- Test and research modes for local development
- Modern Python project structure

---

## 📋 Prerequisites

- Python 3.12+
- Telegram account and bot token
- OpenAI API key
- [requirements.txt](requirements.txt) dependencies

---

## ⚙️ Environment Setup

### 1. Create Telegram Bot

1. Start a chat with [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` command and follow the instructions
3. Note down your bot token (e.g., `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
4. Get your Chat ID:
   - Send a message to your bot
   - Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find your chat ID in the response

### 2. Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```env
# OpenAI API Configuration
OPENAI_API_KEY=sk-proj-your_openai_api_key_here

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Webhook Configuration (optional - for production deployment)
WEBHOOK_URL=https://your-domain.com/webhook/telegram

# Server Configuration (optional - defaults provided)
ENDPOINT_HOST=0.0.0.0
ENDPOINT_PORT=8000
```

---

## � Quick Start Options

### Option 1: VS Code Dev Container (Recommended)

The fastest way to get started! Everything is pre-configured in a containerized environment.

**Prerequisites:**
- VS Code with Dev Containers extension
- Docker Desktop

**Setup:**
1. Open the project in VS Code
2. Click **"Reopen in Container"** when prompted
3. Wait for the container to build (~2-3 minutes first time)
4. Create `.env` file with your API keys (see Environment Setup below)
5. Run: `python src/main.py -test`

📖 **[Complete Dev Container Guide](DEV-CONTAINER-GUIDE.md)**

**What you get:**
- ✅ Python 3.12 with all dependencies
- ✅ Redis server running
- ✅ VS Code debugging and testing
- ✅ Code quality tools (black, mypy, flake8)
- ✅ Pre-commit hooks
- ✅ Hot reload development

### Option 2: Docker Compose

Run the complete stack with Docker:
```bash
# Development environment
docker-compose up -d

# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

📖 **[Complete Docker Guide](DOCKER.md)**

### Option 3: Local Installation

Traditional Python setup:

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd stock-tracker-agent
   ```

2. Install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

---

## 🚀 Running the Project

### Production Mode

Run the agent as a web service:

```bash
python src/main.py
```

This will:
- Start the FastAPI web server on port 8000
- Begin tracking stocks every hour
- Listen for Telegram webhooks at `/webhook/telegram`

### Test Mode

Run the agent in test mode for local development:

```bash
python src/main.py -test
```

This will:
- Start a chat terminal for manual interaction
- Track stocks every minute (more frequent for testing)
- Allow you to test commands locally

### Research Mode

Test the research pipeline for a specific stock:

```bash
python src/main.py -test -research AAPL
```

This will immediately run the research pipeline for the specified stock symbol.

---

## 🤖 Telegram Commands

Send these commands to your Telegram bot:

- **Add a stock**: `Start tracking AAPL` or `Add MSFT to tracker`
- **Remove a stock**: `Stop tracking MSFT` or `Remove AAPL`
- **List tracked stocks**: `What stocks am I tracking?` or `Show my tracker list`
- **Get stock price**: `What is the price of AAPL?` or `TSLA price`

The agent uses natural language processing, so you can phrase commands naturally!

---

## 🔗 Webhook Setup (Production)

For production deployment, set up a webhook so Telegram can send updates to your server:

### Using the API

Once your server is running, you can set the webhook:

```bash
# Set webhook
curl -X POST "http://localhost:8000/webhook/set?webhook_url=https://your-domain.com/webhook/telegram"

# Check webhook status
curl "http://localhost:8000/webhook/info"

# Delete webhook (if needed)
curl -X DELETE "http://localhost:8000/webhook"
```

### Using ngrok (for testing)

1. Install [ngrok](https://ngrok.com/)
2. Start your application: `python main.py`
3. In another terminal: `ngrok http 8000`
4. Copy the HTTPS URL provided by ngrok
5. Set the webhook: `curl -X POST "http://localhost:8000/webhook/set?webhook_url=https://your-ngrok-url.ngrok.io/webhook/telegram"`

---

## 🐳 Docker Deployment

### Development Environment

The easiest way to get started is using Docker for development:

```bash
# Validate Docker setup
./scripts/validate-docker.sh

# Start development environment
./scripts/dev.sh start

# View logs
./scripts/dev.sh logs

# Run tests
./scripts/dev.sh test

# Stop environment
./scripts/dev.sh stop
```

**Development services:**
- Application: http://localhost
- Direct API: http://localhost:8000
- Redis: localhost:6379

### Production Deployment

For production deployment:

```bash
# Set up SSL certificates (see docker/nginx/ssl/README.md)
# Then deploy
./scripts/prod.sh deploy

# Check status
./scripts/prod.sh status

# Create backups
./scripts/prod.sh backup

# View logs
./scripts/prod.sh logs
```

**Production features:**
- HTTPS with SSL certificates
- Redis persistence
- Log rotation
- Health monitoring
- Automatic restart policies

### Manual Docker Commands

If you prefer manual control:

1. **Build and Run Development**:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

2. **Build and Run Production**:
   ```bash
   docker-compose -f docker-compose.prod.yml build
   docker-compose -f docker-compose.prod.yml up -d
   ```

For detailed Docker documentation, see [DOCKER.md](DOCKER.md).

---

## 🛠️ Project Structure

```
stock-tracker-agent/
├── src/
│   ├── main.py                      # Application entry point
│   └── stock_tracker/
│       ├── __init__.py
│       ├── api/                      # FastAPI application
│       │   ├── __init__.py
│       │   └── app.py               # Web endpoints and webhook handling
│       ├── agents/                   # AI agents
│       │   ├── __init__.py
│       │   └── handlers.py          # Message processing and research
│       ├── core/                     # Core business logic
│       │   ├── __init__.py
│       │   ├── stock_checker.py     # Stock price fetching
│       │   ├── tools.py             # Agent tools for stock operations
│       │   └── tracker.py           # Stock tracking and monitoring
│       ├── notifications/            # Notification services
│       │   ├── __init__.py
│       │   └── telegram.py          # Telegram bot integration
│       └── utils/                    # Utilities and configuration
│           ├── __init__.py
│           └── config.py            # Configuration and validation
├── resources/                        # Data storage
│   ├── alert_history.json           # Track sent alerts
│   └── tracker_list.json           # Tracked stocks list
├── requirements.txt                  # Python dependencies
├── pyproject.toml                   # Modern Python project configuration
├── .env.example                     # Environment variables template
├── Dockerfile                       # Docker configuration
├── docker-compose.yml              # Docker Compose setup
└── README.md                        # This file
```

---

## 📝 How It Works

1. **Tracking**: The agent checks prices for stocks in your tracker list every hour (or every minute in test mode)
2. **Alerting**: If a stock moves >1% up or down from previous close, the agent:
   - Runs a research pipeline to analyze news and market events
   - Summarizes findings in under 160 characters
   - Sends a Telegram message alert to your chat
3. **Interaction**: You can add/remove stocks by sending natural language commands to the Telegram bot
4. **Webhook**: In production, Telegram sends user messages to your server via webhook

---

## 🔧 API Endpoints

- `GET /` - Health check
- `GET /health` - Health status
- `POST /webhook/telegram` - Telegram webhook endpoint
- `POST /webhook/set` - Set webhook URL
- `GET /webhook/info` - Get webhook information
- `DELETE /webhook` - Delete webhook

---

## 🐛 Troubleshooting

### Environment Variables
- Ensure your `.env` file contains all required variables
- Verify your Telegram bot token is correct
- Check that your chat ID is accurate (numeric, not username)

### Telegram Bot Setup
- Make sure you've started a conversation with your bot
- The bot must receive at least one message from you to get your chat ID
- Verify webhook URL is publicly accessible (use ngrok for testing)

### Stock Tracking
- Check that stock symbols are valid (use uppercase, e.g., 'AAPL' not 'aapl')
- Ensure OpenAI API key has sufficient credits
- Review logs for error details

### Common Issues
- **Bot doesn't respond**: Check webhook setup and server logs
- **No price alerts**: Verify stocks are added to tracker and moving >1%
- **Import errors**: Ensure all dependencies are installed from requirements.txt

---

## 🧪 Development

### Running Tests

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests (when test files are added)
pytest

# Code formatting
black src/

# Type checking
mypy src/
```

### Project Development

The project follows modern Python practices:
- **src/ layout**: Clean package structure
- **Type hints**: Improved code quality and IDE support
- **Async/await**: Efficient handling of I/O operations
- **Environment variables**: Secure configuration management
- **Modular design**: Separated concerns for maintainability

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Ensure code follows project standards (`black`, `mypy`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

---

## 📞 Support

For issues and questions:
- Create an issue in the repository
- Check existing documentation
- Review logs for error details
- Verify environment configuration

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Enjoy automated stock tracking and market insights delivered straight to your Telegram! 📈📱**
