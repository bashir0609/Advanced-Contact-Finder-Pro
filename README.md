# 🎯 Advanced Contact Finder Pro - Deployment Guide

## 🚀 Quick Start for Streamlit Cloud

### 1. Repository Setup
```bash
# Create new repository with these files:
├── app.py                    # Main application (enhanced_contact_finder.py)
├── requirements.txt          # Python dependencies
├── .env.template            # API keys template
└── README.md               # This guide
```

### 2. Deploy to Streamlit Cloud
1. Push code to GitHub/GitLab
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Set main file as `app.py`
5. Deploy!

### 3. Configure API Keys (Optional but Recommended)
Add these in Streamlit Cloud Secrets:
```toml
[secrets]
OPENROUTER_API_KEY = "your_key_here"
TAVILY_API_KEY = "your_key_here"
OPENAI_API_KEY = "your_key_here"
```

## 🔑 API Keys & Pricing

### Free Options
- **WHOIS Lookup**: No API key needed
- **Website Scraping**: No API key needed  
- **Basic Web Search**: No API key needed (limited)

### Paid APIs (Recommended)
| Service | Use Case | Cost | Get Key |
|---------|----------|------|---------|
| **OpenRouter** | AI Research + Web Search | $0.20-$1/1M tokens | [openrouter.ai](https://openrouter.ai) |
| **Tavily** | Enhanced Web Search | $5/1K searches | [tavily.com](https://tavily.com) |
| **OpenAI** | Traditional AI Research | $0.15-$15/1M tokens | [platform.openai.com](https://platform.openai.com) |

## 🛠️ Key Features & Improvements

### ✅ Fixed Issues from Original Code
- **Real Web Search**: Added actual web search APIs (Tavily, Bing, DuckDuckGo)
- **Enhanced Scraping**: Better error handling, anti-bot detection avoidance
- **Cloud Compatible**: Removed dependencies that don't work in Streamlit Cloud
- **Rate Limiting**: Proper delays and retry logic
- **Multi-language Support**: German, English, French, Spanish patterns

### 🌟 New Capabilities
- **Real-time Web Search**: Live internet search via Perplexity/Tavily
- **Multi-source Discovery**: Business directories, professional networks, news
- **Smart Email Categorization**: Executive, sales, support, HR, etc.
- **Enhanced Export**: CSV, JSON with metadata
- **Progress Tracking**: Real-time progress bars and status updates

## 📖 Usage Instructions

### Basic Usage (No API Keys)
1. Enter company name and website
2. Select research methods:
   - ✅ Website Scraping
   - ✅ WHOIS Lookup  
   - ✅ Email Patterns
3. Click "Start Research"

### Advanced Usage (With API Keys)
1. Add API keys in sidebar
2. Select all research methods including:
   - ✅ Real-time Web Search
   - ✅ AI Research Assistant
3. Choose web-enabled AI models for best results
4. Adjust advanced options (max pages, search depth)

### Best Results Strategy
```
1. Start with OpenRouter API key (Perplexity models)
2. Enable all research methods
3. Use "Deep" or "Comprehensive" search depth
4. For German companies: Include "impressum" in manual search
5. Export results in both CSV and JSON formats
```

## 🎯 Research Methods Explained

### 🌐 Real-time Web Search
- Uses Tavily/Bing APIs for live web search
- Searches business directories, news articles, press releases
- Extracts contacts from search results
- **Best for**: Finding recent contact information

### 🤖 AI Research Assistant  
- Uses Perplexity (web-enabled) or traditional AI models
- Analyzes multiple sources and provides structured results
- Creates markdown tables with contact information
- **Best for**: Comprehensive analysis and verification

### 🌍 Website Scraping
- Scans company website and contact pages
- Supports multiple languages (English, German, French, Spanish)
- Extracts emails from HTML, mailto links, structured data
- **Best for**: Official company contact information

### 📋 WHOIS Lookup
- Domain registration information
- Administrative and technical contacts
- Company registration details
- **Best for**: Technical contacts and domain ownership

## 🌍 Country-Specific Features

### 🇩🇪 Germany
- Impressum page scanning (legally required contact info)
- Xing profile suggestions (German LinkedIn)
- German business patterns (Geschäftsführer, etc.)
- German email patterns (kontakt@, bewerbung@)

### 🇺🇸 United States
- LinkedIn company page focus
- Business directory integration
- Chamber of Commerce suggestions
- Standard US business patterns

### 🌐 International
- Multi-language contact page detection
- Regional business directory suggestions
- Country-specific professional networks
- Localized email patterns

## 📊 Export & Results

### Export Formats
- **CSV**: Spreadsheet-compatible with metadata
- **JSON**: Machine-readable with full research context
- **Text**: Quick copy-paste format

### Results Include
- Contact categorization (Executive, Sales, Support, etc.)
- Source attribution (which method found each contact)
- Confidence levels (High/Medium/Low)
- Research metadata and timestamps

## 🔧 Troubleshooting

### Common Issues
```
❌ "No contacts found"
✅ Try: Different research methods, manual verification, direct company contact

❌ "API key required"  
✅ Try: Add API key in sidebar or use free methods only

❌ "Request timeout"
✅ Try: Reduce max pages to scrape, check internet connection

❌ "Website blocking requests"
✅ Try: AI research method, manual research guide
```

### Performance Tips
- Start with 10-15 max pages for scraping
- Use "Standard" search depth initially  
- Enable web-enabled AI models for best results
- Add multiple API keys for redundancy

## 🚨 Legal & Ethical Considerations

### ✅ Ethical Use
- Respect robots.txt files
- Rate limiting to avoid server overload
- Focus on publicly available information
- Verify information before use

### ⚠️ Legal Compliance
- Follow GDPR/privacy regulations
- Respect website terms of service
- Use contacts only for legitimate business purposes
- Consider data protection requirements

## 📞 Support & Updates

For issues or feature requests:
1. Check troubleshooting section above
2. Verify API keys and internet connection
3. Try different research methods
4. Use manual research guide as fallback

The application is designed to be robust and work even with partial failures, providing multiple research pathways for finding contact information.
