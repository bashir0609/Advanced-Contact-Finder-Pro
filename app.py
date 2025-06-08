import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
import validators
import whois
from urllib.parse import urlparse, urljoin, quote
import time
import json
from dotenv import load_dotenv
import os
import threading
from queue import Queue
from bs4 import BeautifulSoup
import random
import concurrent.futures
from typing import Dict, List, Set, Tuple
import ssl
import urllib3

# Disable SSL warnings for cloud deployment
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# Enhanced model configurations with real web search capabilities
MODEL_CONFIGS = {
    "web_search": {
        "perplexity": {
            "name": "🌐 Perplexity (Real-time Web)",
            "models": {
                "perplexity/llama-3-sonar-large-online": "Sonar Large Online ($1/1M)",
                "perplexity/llama-3-sonar-small-online": "Sonar Small Online ($0.20/1M)"
            },
            "api_url": "https://openrouter.ai/api/v1/chat/completions",
            "requires_key": True,
            "real_time": True,
            "key_env": "OPENROUTER_API_KEY"
        },
        "tavily": {
            "name": "🔍 Tavily Search",
            "api_url": "https://api.tavily.com/search",
            "requires_key": True,
            "real_time": True,
            "key_env": "TAVILY_API_KEY"
        }
    },
    "traditional": {
        "openai": {
            "name": "🧠 OpenAI GPT",
            "models": {
                "gpt-4o": "GPT-4o ($15/1M)",
                "gpt-4o-mini": "GPT-4o Mini ($0.15/1M)"
            },
            "api_url": "https://api.openai.com/v1/chat/completions",
            "requires_key": True,
            "real_time": False,
            "key_env": "OPENAI_API_KEY"
        },
        "anthropic": {
            "name": "🤖 Claude",
            "models": {
                "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet ($3/1M)",
                "claude-3-5-haiku-20241022": "Claude 3.5 Haiku ($0.25/1M)"
            },
            "api_url": "https://api.anthropic.com/v1/messages",
            "requires_key": True,
            "real_time": False,
            "key_env": "ANTHROPIC_API_KEY"
        }
    }
}

class RealTimeWebSearcher:
    """Real-time web search using multiple search engines and APIs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def search_tavily(self, query: str, api_key: str, max_results: int = 5) -> List[Dict]:
        """Search using Tavily API for real-time results"""
        if not api_key:
            return []
        
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "include_domains": [],
                    "exclude_domains": ["facebook.com", "twitter.com", "instagram.com"],
                    "max_results": max_results,
                    "include_answer": True,
                    "include_raw_content": True
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                st.warning(f"Tavily search failed: {response.status_code}")
                return []
                
        except Exception as e:
            st.warning(f"Tavily search error: {str(e)}")
            return []
    
    def search_bing(self, query: str, api_key: str = None) -> List[Dict]:
        """Search using Bing Web Search API (if available)"""
        if not api_key:
            return []
        
        try:
            headers = {"Ocp-Apim-Subscription-Key": api_key}
            params = {
                "q": query,
                "count": 10,
                "offset": 0,
                "mkt": "en-US",
                "safesearch": "Moderate"
            }
            
            response = requests.get(
                "https://api.bing.microsoft.com/v7.0/search",
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get("webPages", {}).get("value", []):
                    results.append({
                        "title": item.get("name", ""),
                        "url": item.get("url", ""),
                        "content": item.get("snippet", "")
                    })
                return results
            else:
                return []
                
        except Exception as e:
            st.warning(f"Bing search error: {str(e)}")
            return []
    
    def search_duckduckgo(self, query: str) -> List[Dict]:
        """Fallback search using DuckDuckGo (scraping)"""
        try:
            # Use DuckDuckGo instant answer API
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1"
            }
            
            response = requests.get(
                "https://api.duckduckgo.com/",
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                # Extract from related topics
                for topic in data.get("RelatedTopics", []):
                    if isinstance(topic, dict) and "FirstURL" in topic:
                        results.append({
                            "title": topic.get("Text", "")[:100],
                            "url": topic.get("FirstURL", ""),
                            "content": topic.get("Text", "")
                        })
                
                return results[:5]
            
            return []
            
        except Exception as e:
            return []

class EnhancedWebScraper:
    """Enhanced web scraper with multiple strategies for reliability"""
    
    def __init__(self):
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        )
        
        self.phone_pattern = re.compile(
            r'(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?)?[0-9]{3}[-.\s]?[0-9]{4}|(?:\+49[-.\s]?)?(?:\(?[0-9]{3,4}\)?[-.\s]?)?[0-9]{6,8}|(?:\+44[-.\s]?)?(?:\(?[0-9]{3,4}\)?[-.\s]?)?[0-9]{6,8}',
            re.IGNORECASE
        )
        
        self.excluded_domains = {
            'example.com', 'test.com', 'domain.com', 'yoursite.com',
            'google.com', 'facebook.com', 'twitter.com', 'linkedin.com',
            'instagram.com', 'youtube.com', 'github.com', 'sentry.io',
            'gravatar.com', 'w3.org', 'schema.org', 'mozilla.org'
        }
        
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
        ]
        
        # Session with connection pooling
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def get_headers(self):
        """Get randomized headers"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
    
    def is_valid_email(self, email: str) -> bool:
        """Enhanced email validation"""
        try:
            if '@' not in email or '.' not in email.split('@')[1]:
                return False
            
            domain = email.split('@')[1].lower()
            if domain in self.excluded_domains:
                return False
            
            # Check for fake/test patterns
            fake_patterns = [
                r'noreply', r'no-reply', r'donotreply', r'test@',
                r'admin@example', r'user@example', r'@example\.com',
                r'placeholder', r'dummy', r'fake'
            ]
            
            for pattern in fake_patterns:
                if re.search(pattern, email.lower()):
                    return False
            
            return True
        except:
            return False
    
    def extract_contacts_from_text(self, text: str) -> Tuple[Set[str], Set[str]]:
        """Extract emails and phones from text"""
        emails = set()
        phones = set()
        
        # Extract emails
        found_emails = self.email_pattern.findall(text)
        for email in found_emails:
            if self.is_valid_email(email):
                emails.add(email.lower())
        
        # Extract phone numbers
        found_phones = self.phone_pattern.findall(text)
        for phone in found_phones:
            cleaned_phone = re.sub(r'[^\d+]', '', phone)
            if len(cleaned_phone) >= 10:
                phones.add(phone)
        
        # Look for obfuscated emails (common anti-spam technique)
        obfuscated_patterns = [
            r'([a-zA-Z0-9._%+-]+)\s*\[?\s*(?:at|@)\s*\]?\s*([a-zA-Z0-9.-]+)\s*\[?\s*(?:dot|\.)\s*\]?\s*([a-zA-Z]{2,})',
            r'([a-zA-Z0-9._%+-]+)\s*\(at\)\s*([a-zA-Z0-9.-]+)\s*\(dot\)\s*([a-zA-Z]{2,})',
            r'([a-zA-Z0-9._%+-]+)\s*AT\s*([a-zA-Z0-9.-]+)\s*DOT\s*([a-zA-Z]{2,})'
        ]
        
        for pattern in obfuscated_patterns:
            obfuscated_emails = re.findall(pattern, text, re.IGNORECASE)
            for local, domain, tld in obfuscated_emails:
                email = f"{local}@{domain}.{tld}".replace(' ', '')
                if self.is_valid_email(email):
                    emails.add(email.lower())
        
        return emails, phones
    
    def safe_request(self, url: str, timeout: int = 15) -> Tuple[requests.Response, str]:
        """Make a safe HTTP request with multiple strategies"""
        headers = self.get_headers()
        
        # Strategy 1: Normal request
        try:
            response = self.session.get(url, headers=headers, timeout=timeout, verify=False)
            response.raise_for_status()
            return response, None
        except requests.exceptions.SSLError:
            # Strategy 2: Disable SSL verification
            try:
                response = self.session.get(url, headers=headers, timeout=timeout, verify=False)
                response.raise_for_status()
                return response, None
            except Exception as e:
                return None, f"SSL error: {str(e)}"
        except requests.exceptions.Timeout:
            return None, "Request timeout"
        except requests.exceptions.RequestException as e:
            return None, f"Request error: {str(e)}"
        except Exception as e:
            return None, f"Unexpected error: {str(e)}"
    
    def scrape_website(self, base_url: str, max_pages: int = 15) -> Dict:
        """Comprehensive website scraping with enhanced URL discovery"""
        all_emails = set()
        all_phones = set()
        pages_scraped = []
        
        # Generate comprehensive URL list
        urls_to_check = [base_url]
        
        domain = urlparse(base_url).netloc
        base_path = f"{urlparse(base_url).scheme}://{domain}"
        
        # Enhanced contact page patterns (multi-language support)
        contact_patterns = [
            # English
            '/contact', '/contact-us', '/contact.html', '/contact.php',
            '/about', '/about-us', '/about.html', '/team', '/staff', '/people',
            '/leadership', '/management', '/executives', '/directory',
            
            # German
            '/kontakt', '/kontakt.html', '/impressum', '/impressum.html',
            '/ueber-uns', '/team', '/mitarbeiter', '/ansprechpartner',
            
            # French
            '/contact', '/nous-contacter', '/equipe', '/a-propos',
            
            # Spanish
            '/contacto', '/equipo', '/sobre-nosotros',
            
            # Common variations
            '/en/contact', '/de/kontakt', '/fr/contact', '/es/contacto',
            '/company', '/corporate', '/office', '/locations'
        ]
        
        for pattern in contact_patterns:
            urls_to_check.append(base_path + pattern)
            urls_to_check.append(base_path + pattern.upper())  # Try uppercase versions
        
        # Scrape each URL with progress tracking
        successful_scrapes = 0
        
        for i, url in enumerate(urls_to_check[:max_pages]):
            try:
                response, error = self.safe_request(url)
                if response and response.status_code == 200:
                    
                    # Parse content
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Remove unwanted elements
                    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        element.decompose()
                    
                    # Extract contacts from text
                    text_content = soup.get_text()
                    emails, phones = self.extract_contacts_from_text(text_content)
                    
                    # Extract from mailto links
                    mailto_links = soup.find_all('a', href=lambda x: x and x.startswith('mailto:'))
                    for link in mailto_links:
                        email = link['href'][7:].split('?')[0]
                        if self.is_valid_email(email):
                            emails.add(email.lower())
                    
                    # Extract from tel links
                    tel_links = soup.find_all('a', href=lambda x: x and x.startswith('tel:'))
                    for link in tel_links:
                        phone = link['href'][4:].strip()
                        if len(re.sub(r'[^\d]', '', phone)) >= 10:
                            phones.add(phone)
                    
                    # Look for structured data (JSON-LD)
                    json_scripts = soup.find_all('script', type='application/ld+json')
                    for script in json_scripts:
                        try:
                            data = json.loads(script.string)
                            if isinstance(data, dict):
                                # Extract emails and phones from structured data
                                if 'email' in data:
                                    if self.is_valid_email(data['email']):
                                        emails.add(data['email'].lower())
                                if 'telephone' in data:
                                    phones.add(data['telephone'])
                        except:
                            continue
                    
                    all_emails.update(emails)
                    all_phones.update(phones)
                    
                    if emails or phones:
                        successful_scrapes += 1
                        pages_scraped.append({
                            'url': url,
                            'emails_found': len(emails),
                            'phones_found': len(phones),
                            'status': 'success'
                        })
                
                # Rate limiting
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                pages_scraped.append({
                    'url': url,
                    'emails_found': 0,
                    'phones_found': 0,
                    'status': f'error: {str(e)}'
                })
        
        return {
            'emails': all_emails,
            'phones': all_phones,
            'pages_scraped': pages_scraped,
            'successful_scrapes': successful_scrapes
        }

class ComprehensiveContactFinder:
    """Main class orchestrating all contact finding methods"""
    
    def __init__(self):
        self.web_searcher = RealTimeWebSearcher()
        self.web_scraper = EnhancedWebScraper()
        self.api_keys = self.load_api_keys()
    
    def load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment and session state"""
        keys = {}
        all_configs = {**MODEL_CONFIGS["web_search"], **MODEL_CONFIGS["traditional"]}
        
        for provider, config in all_configs.items():
            if config.get("key_env"):
                key_name = config["key_env"].lower().replace("_api_key", "")
                keys[key_name] = (
                    os.getenv(config["key_env"]) or 
                    st.session_state.get(f"{key_name}_key", "")
                )
        
        return keys
    
    def search_with_ai(self, company: str, website: str, country: str, 
                      provider: str, model: str, api_key: str, industry: str = "") -> str:
        """Search using AI models with enhanced prompts"""
        
        domain = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
        
        # Create comprehensive search prompt
        prompt = f"""
You are a professional business research assistant specializing in finding verified contact information.

**RESEARCH TARGET**: {company}
**WEBSITE**: {website}
**LOCATION**: {country}
{"**INDUSTRY**: " + industry if industry else ""}

**OBJECTIVE**: Find current, verified contact information for key personnel, executives, and general business contacts.

**SEARCH STRATEGY**:
1. **Official Company Sources**: Website contact pages, about sections, team directories, impressum (German companies)
2. **Professional Networks**: LinkedIn profiles, Xing profiles (German), business directories
3. **Business Intelligence**: Press releases, news articles, company announcements
4. **Public Records**: Business registrations, chamber of commerce listings
5. **Industry Sources**: Trade publications, conference speakers, industry directories

**OUTPUT FORMAT**:
Return a markdown table with these columns:
| Name | Role | Email | Phone | LinkedIn/Xing URL | Source | Confidence |

**GUIDELINES**:
- Focus on current employees and decision-makers
- Include general contact information (info@, contact@, sales@)
- Mark estimated emails as "(estimated)" 
- Provide confidence levels: High/Medium/Low
- For German companies, check impressum pages (legally required)

**EXAMPLE OUTPUT**:
| Name | Role | Email | Phone | LinkedIn/Xing URL | Source | Confidence |
|------|------|-------|-------|-------------------|--------|------------|
| John Smith | CEO | j.smith@{domain} | +1-555-0123 | linkedin.com/in/johnsmith | Company Website | High |
| | General Contact | info@{domain} | +1-555-0100 | | Website Contact Page | High |
| Jane Doe | HR Director | hr@{domain} | | xing.com/profile/janedoe | Business Directory | Medium |

**VERIFICATION**: Cross-reference multiple sources when possible.

**SOURCES**: List all sources used with URLs.

Begin comprehensive research for {company} now.
"""
        
        try:
            if provider == "perplexity":
                return self.query_openrouter(prompt, model, api_key)
            elif provider == "openai":
                return self.query_openai(prompt, model, api_key)
            elif provider == "anthropic":
                return self.query_anthropic(prompt, model, api_key)
            else:
                return "Provider not implemented"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def query_openrouter(self, prompt: str, model: str, api_key: str) -> str:
        """Query OpenRouter API (Perplexity)"""
        if not api_key:
            return "❌ OpenRouter API key required"
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 4000
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"OpenRouter error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"OpenRouter error: {str(e)}"
    
    def query_openai(self, prompt: str, model: str, api_key: str) -> str:
        """Query OpenAI API"""
        if not api_key:
            return "❌ OpenAI API key required"
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 4000
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"OpenAI error: {response.status_code}"
                
        except Exception as e:
            return f"OpenAI error: {str(e)}"
    
    def query_anthropic(self, prompt: str, model: str, api_key: str) -> str:
        """Query Anthropic API"""
        if not api_key:
            return "❌ Anthropic API key required"
        
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": model,
                    "max_tokens": 4000,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()["content"][0]["text"]
            else:
                return f"Anthropic error: {response.status_code}"
                
        except Exception as e:
            return f"Anthropic error: {str(e)}"
    
    def search_web_sources(self, company: str, website: str, country: str) -> Dict:
        """Search web sources for contact information"""
        all_results = []
        
        # Search queries for different types of information
        search_queries = [
            f'"{company}" contact email phone {country}',
            f'"{company}" executives management team',
            f'"{company}" employee directory staff',
            f'site:{urlparse(website).netloc} contact email',
            f'"{company}" press release contact spokesperson',
            f'"{company}" business directory listing'
        ]
        
        if country.lower() in ['germany', 'deutschland']:
            search_queries.append(f'"{company}" impressum kontakt')
        
        # Try Tavily search if API key available
        tavily_key = self.api_keys.get('tavily', '')
        if tavily_key:
            for query in search_queries[:3]:  # Limit for API costs
                results = self.web_searcher.search_tavily(query, tavily_key)
                all_results.extend(results)
                time.sleep(1)  # Rate limiting
        
        # Try Bing search if API key available
        bing_key = self.api_keys.get('bing', '')
        if bing_key:
            for query in search_queries[:2]:
                results = self.web_searcher.search_bing(query, bing_key)
                all_results.extend(results)
                time.sleep(1)
        
        # Fallback to DuckDuckGo
        if not tavily_key and not bing_key:
            for query in search_queries[:2]:
                results = self.web_searcher.search_duckduckgo(query)
                all_results.extend(results)
                time.sleep(2)
        
        # Extract contacts from search results
        all_emails = set()
        all_phones = set()
        
        for result in all_results:
            content = f"{result.get('title', '')} {result.get('content', '')}"
            emails, phones = self.web_scraper.extract_contacts_from_text(content)
            all_emails.update(emails)
            all_phones.update(phones)
        
        return {
            'emails': all_emails,
            'phones': all_phones,
            'results_found': len(all_results),
            'search_results': all_results[:10]  # Keep top 10 for display
        }

def get_whois_info(domain: str) -> Dict:
    """Enhanced WHOIS information extraction"""
    try:
        w = whois.whois(domain)
        info = {}
        
        if hasattr(w, 'emails') and w.emails:
            emails = w.emails if isinstance(w.emails, list) else [w.emails]
            # Filter out generic registrar emails
            filtered_emails = [email for email in emails 
                             if not any(generic in email.lower() 
                                      for generic in ['whoisguard', 'proxy', 'privacy', 'registrar'])]
            if filtered_emails:
                info['emails'] = list(set(filtered_emails))
        
        if hasattr(w, 'org') and w.org:
            info['organization'] = w.org
        
        if hasattr(w, 'registrar') and w.registrar:
            info['registrar'] = w.registrar
        
        if hasattr(w, 'creation_date') and w.creation_date:
            creation_date = w.creation_date
            if isinstance(creation_date, list):
                creation_date = creation_date[0]
            if creation_date:
                info['creation_date'] = creation_date.strftime('%Y-%m-%d')
        
        return info
    except Exception as e:
        return {"error": str(e)}

def categorize_emails(emails: List[str]) -> Dict[str, List[str]]:
    """Enhanced email categorization"""
    categories = {
        'executive': [],
        'sales': [],
        'support': [],
        'hr': [],
        'general': [],
        'technical': [],
        'marketing': [],
        'finance': [],
        'personal': []
    }
    
    patterns = {
        'executive': [r'ceo', r'president', r'director', r'manager', r'chief', r'geschaeftsfueh', r'vorstand'],
        'sales': [r'sales', r'business', r'commercial', r'vertrieb', r'verkauf'],
        'support': [r'support', r'help', r'service', r'kunde', r'customer'],
        'hr': [r'hr', r'personal', r'bewerbung', r'career', r'jobs', r'recruiting'],
        'technical': [r'tech', r'it', r'dev', r'admin', r'webmaster', r'engineering'],
        'marketing': [r'marketing', r'promotion', r'pr', r'media', r'communication'],
        'finance': [r'finance', r'accounting', r'billing', r'invoice', r'buchhal'],
        'general': [r'info', r'contact', r'office', r'hello', r'kontakt', r'mail']
    }
    
    for email in emails:
        local_part = email.split('@')[0].lower()
        categorized = False
        
        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, local_part):
                    categories[category].append(email)
                    categorized = True
                    break
            if categorized:
                break
        
        if not categorized:
            # Check if it looks like a personal email (firstname.lastname pattern)
            if '.' in local_part and len(local_part.split('.')) == 2:
                categories['personal'].append(email)
            else:
                categories['general'].append(email)
    
    return {k: v for k, v in categories.items() if v}

def generate_email_patterns(domain: str, country: str = "", industry: str = "") -> Dict[str, List[str]]:
    """Generate comprehensive email patterns"""
    patterns = {
        "Standard Business": [
            f"info@{domain}",
            f"contact@{domain}",
            f"hello@{domain}",
            f"office@{domain}",
            f"mail@{domain}",
            f"admin@{domain}"
        ],
        "Executive": [
            f"ceo@{domain}",
            f"president@{domain}",
            f"director@{domain}",
            f"manager@{domain}",
            f"leadership@{domain}"
        ],
        "Departments": [
            f"sales@{domain}",
            f"marketing@{domain}",
            f"hr@{domain}",
            f"support@{domain}",
            f"finance@{domain}",
            f"operations@{domain}"
        ]
    }
    
    # Country-specific patterns
    if country.lower() in ['germany', 'deutschland', 'de']:
        patterns["German Business"] = [
            f"kontakt@{domain}",
            f"personal@{domain}",
            f"bewerbung@{domain}",
            f"geschaeftsleitung@{domain}",
            f"verwaltung@{domain}",
            f"vertrieb@{domain}"
        ]
    
    # Industry-specific patterns
    if industry:
        industry_lower = industry.lower()
        if any(word in industry_lower for word in ['education', 'school', 'university', 'bildung']):
            patterns["Education"] = [
                f"admissions@{domain}",
                f"registrar@{domain}",
                f"faculty@{domain}",
                f"academic@{domain}",
                f"students@{domain}"
            ]
        elif any(word in industry_lower for word in ['tech', 'technology', 'software']):
            patterns["Technology"] = [
                f"dev@{domain}",
                f"tech@{domain}",
                f"engineering@{domain}",
                f"product@{domain}",
                f"api@{domain}"
            ]
        elif any(word in industry_lower for word in ['healthcare', 'medical', 'hospital']):
            patterns["Healthcare"] = [
                f"appointments@{domain}",
                f"patients@{domain}",
                f"medical@{domain}",
                f"clinic@{domain}"
            ]
    
    return patterns

def parse_markdown_table(text: str) -> pd.DataFrame:
    """Enhanced markdown table parser"""
    try:
        lines = text.split("\n")
        table_lines = [line for line in lines if "|" in line and "---" not in line and line.strip()]
        
        if len(table_lines) < 2:
            return None
        
        # Parse headers
        headers = [cell.strip() for cell in table_lines[0].split("|") if cell.strip()]
        if not headers:
            return None
        
        # Parse rows
        rows = []
        for line in table_lines[1:]:
            cells = [cell.strip() for cell in line.split("|")]
            # Remove empty cells at the beginning and end
            while cells and not cells[0]:
                cells.pop(0)
            while cells and not cells[-1]:
                cells.pop()
            
            # Ensure row has the same number of columns as headers
            while len(cells) < len(headers):
                cells.append("")
            if len(cells) > len(headers):
                cells = cells[:len(headers)]
            
            # Only include rows with meaningful content
            if any(cell.strip() for cell in cells):
                rows.append(cells)
        
        if not rows:
            return None
        
        return pd.DataFrame(rows, columns=headers)
    except Exception as e:
        return None

def main():
    st.set_page_config(
        page_title="Advanced Contact Finder Pro",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🎯 Advanced Contact Finder Pro")
    st.markdown("*Real-time Web Search + AI Research + Enhanced Scraping + Multi-Source Discovery*")
    
    # Initialize the contact finder
    contact_finder = ComprehensiveContactFinder()
    
    # Sidebar configuration
    with st.sidebar:
        st.header("🛠️ Research Configuration")
        
        # Research methods selection
        research_methods = st.multiselect(
            "Select Research Methods",
            [
                "🌐 Real-time Web Search",
                "🤖 AI Research Assistant", 
                "🌍 Website Scraping",
                "📋 WHOIS Lookup",
                "📧 Email Patterns",
                "🔍 Manual Research Guide"
            ],
            default=["🌐 Real-time Web Search", "🤖 AI Research Assistant", "🌍 Website Scraping", "📋 WHOIS Lookup"]
        )
        
        st.markdown("---")
        
        # AI Configuration
        if "🤖 AI Research Assistant" in research_methods:
            st.subheader("🤖 AI Assistant Settings")
            
            ai_tier = st.radio(
                "AI Model Type", 
                ["🌐 Web-enabled (Recommended)", "🧠 Traditional"],
                help="Web-enabled models have real-time internet access"
            )
            
            tier_key = "web_search" if "Web-enabled" in ai_tier else "traditional"
            
            provider = st.selectbox(
                "AI Provider",
                list(MODEL_CONFIGS[tier_key].keys()),
                format_func=lambda x: MODEL_CONFIGS[tier_key][x]["name"]
            )
            
            config = MODEL_CONFIGS[tier_key][provider]
            
            if "models" in config:
                model = st.selectbox(
                    "Model",
                    list(config["models"].keys()),
                    format_func=lambda x: config["models"][x]
                )
            else:
                model = None
            
            st.info(f"🌐 Real-time: {'✅' if config['real_time'] else '❌'}")
            
            # API key input
            api_key = None
            if config["requires_key"]:
                key_name = config["key_env"].lower().replace("_api_key", "") if config["key_env"] else provider
                api_key = st.text_input(f"🔑 {config['name']} API Key", type="password", key=f"{provider}_key")
        
        # Web search configuration
        if "🌐 Real-time Web Search" in research_methods:
            st.subheader("🌐 Web Search Settings")
            
            # Tavily API key
            tavily_key = st.text_input("🔍 Tavily API Key (Optional)", type="password", help="For enhanced web search results")
            if tavily_key:
                st.session_state['tavily_key'] = tavily_key
            
            # Bing API key
            bing_key = st.text_input("🔍 Bing Search API Key (Optional)", type="password", help="For Microsoft Bing search")
            if bing_key:
                st.session_state['bing_key'] = bing_key
        
        st.markdown("---")
        st.caption("💡 **Pro Tip**: Use web-enabled AI models with API keys for best results")
    
    # Main input form
    col1, col2 = st.columns(2)
    
    with col1:
        company = st.text_input("🏢 Company Name", placeholder="e.g., Tesla Inc, BBW Berufsbildungswerk Hamburg")
        website = st.text_input("🌐 Website", placeholder="e.g., tesla.com, bbw.de")
    
    with col2:
        country = st.text_input("📍 Country/Region", value="Germany", placeholder="e.g., Germany, United States")
        industry = st.text_input("🏭 Industry (Optional)", placeholder="e.g., Automotive, Education, Technology")
    
    # Advanced options
    with st.expander("⚙️ Advanced Options"):
        col1, col2 = st.columns(2)
        with col1:
            max_pages = st.slider("Max Pages to Scrape", 5, 30, 15)
            search_depth = st.selectbox("Search Depth", ["Standard", "Deep", "Comprehensive"], index=1)
        with col2:
            include_patterns = st.checkbox("Include Email Patterns", True)
            export_format = st.selectbox("Export Format", ["CSV", "JSON", "Both"], index=2)
    
    # Search button
    search_button = st.button("🚀 Start Comprehensive Contact Research", type="primary", use_container_width=True)
    
    if search_button:
        if not all([company, website]):
            st.error("❌ Please fill in company name and website")
            return
        
        # Validate website
        if not website.startswith(('http://', 'https://')):
            website = 'https://' + website
        if not validators.url(website):
            st.error("❌ Invalid website URL")
            return
        
        domain = urlparse(website).netloc.replace('www.', '')
        
        # Initialize results tracking
        total_methods = len(research_methods)
        current_method = 0
        overall_progress = st.progress(0)
        status_text = st.empty()
        
        # Results storage
        all_emails = set()
        all_phones = set()
        method_results = {}
        research_sources = []
        
        try:
            # Method 1: WHOIS Lookup
            if "📋 WHOIS Lookup" in research_methods:
                current_method += 1
                status_text.text("📋 Performing WHOIS domain lookup...")
                overall_progress.progress(current_method / total_methods * 0.15)
                
                with st.expander("📋 WHOIS Domain Information", expanded=True):
                    whois_info = get_whois_info(domain)
                    
                    if whois_info and 'error' not in whois_info:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if 'organization' in whois_info:
                                st.info(f"**🏢 Registered Organization**: {whois_info['organization']}")
                            if 'registrar' in whois_info:
                                st.info(f"**🌐 Registrar**: {whois_info['registrar']}")
                            if 'creation_date' in whois_info:
                                st.info(f"**📅 Created**: {whois_info['creation_date']}")
                        
                        with col2:
                            if 'emails' in whois_info:
                                whois_emails = set(email.lower() for email in whois_info['emails'])
                                all_emails.update(whois_emails)
                                method_results['whois'] = whois_emails
                                st.success(f"**📧 Contact Emails Found**: {len(whois_emails)}")
                                for email in whois_info['emails']:
                                    st.code(email)
                    else:
                        st.warning("⚠️ No WHOIS contact information available or domain protected")
            
            # Method 2: Website Scraping
            if "🌍 Website Scraping" in research_methods:
                current_method += 1
                status_text.text("🌍 Scraping company website and contact pages...")
                overall_progress.progress(current_method / total_methods * 0.35)
                
                with st.expander("🌍 Website Scraping Results", expanded=True):
                    scraping_progress = st.progress(0)
                    scraping_status = st.empty()
                    
                    scraping_status.text(f"🔍 Scanning {max_pages} pages for contact information...")
                    scraping_progress.progress(25)
                    
                    scraping_results = contact_finder.web_scraper.scrape_website(website, max_pages)
                    
                    scraping_progress.progress(100)
                    scraping_status.text("✅ Website scraping completed!")
                    
                    if scraping_results['emails'] or scraping_results['phones']:
                        # Display metrics
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Pages Scraped", len(scraping_results['pages_scraped']))
                        col2.metric("Successful Scrapes", scraping_results['successful_scrapes'])
                        col3.metric("Emails Found", len(scraping_results['emails']))
                        col4.metric("Phones Found", len(scraping_results['phones']))
                        
                        all_emails.update(scraping_results['emails'])
                        all_phones.update(scraping_results['phones'])
                        method_results['website_scraping'] = scraping_results['emails']
                        
                        # Show successful pages
                        successful_pages = [p for p in scraping_results['pages_scraped'] if p['status'] == 'success']
                        if successful_pages:
                            st.markdown("**✅ Successful Pages:**")
                            for page in successful_pages[:5]:  # Show top 5
                                st.markdown(f"• {page['url']} - {page['emails_found']} emails, {page['phones_found']} phones")
                    else:
                        st.warning("No contacts found during website scraping")
                    
                    time.sleep(1)
                    scraping_progress.empty()
                    scraping_status.empty()
            
            # Method 3: Real-time Web Search
            if "🌐 Real-time Web Search" in research_methods:
                current_method += 1
                status_text.text("🌐 Searching web sources for contact information...")
                overall_progress.progress(current_method / total_methods * 0.55)
                
                with st.expander("🌐 Real-time Web Search Results", expanded=True):
                    web_progress = st.progress(0)
                    web_status = st.empty()
                    
                    web_status.text("🔍 Searching multiple web sources...")
                    web_progress.progress(50)
                    
                    # Update API keys from sidebar
                    if 'tavily_key' in st.session_state:
                        contact_finder.api_keys['tavily'] = st.session_state['tavily_key']
                    if 'bing_key' in st.session_state:
                        contact_finder.api_keys['bing'] = st.session_state['bing_key']
                    
                    web_results = contact_finder.search_web_sources(company, website, country)
                    
                    web_progress.progress(100)
                    web_status.text("✅ Web search completed!")
                    
                    if web_results['emails'] or web_results['phones']:
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Search Results", web_results['results_found'])
                        col2.metric("Emails Found", len(web_results['emails']))
                        col3.metric("Phones Found", len(web_results['phones']))
                        
                        all_emails.update(web_results['emails'])
                        all_phones.update(web_results['phones'])
                        method_results['web_search'] = web_results['emails']
                        
                        # Show top search results
                        if web_results['search_results']:
                            st.markdown("**🔍 Top Search Results:**")
                            for i, result in enumerate(web_results['search_results'][:3], 1):
                                st.markdown(f"{i}. **{result.get('title', 'N/A')}**")
                                if result.get('url'):
                                    st.markdown(f"   🔗 [{result['url']}]({result['url']})")
                    else:
                        st.warning("No contacts found in web search results")
                    
                    time.sleep(1)
                    web_progress.empty()
                    web_status.empty()
            
            # Method 4: AI Research
            if "🤖 AI Research Assistant" in research_methods:
                current_method += 1
                status_text.text("🤖 Conducting AI-powered research...")
                overall_progress.progress(current_method / total_methods * 0.80)
                
                if config["requires_key"] and not api_key:
                    st.error("❌ API key required for AI research")
                else:
                    with st.expander("🤖 AI Research Assistant Results", expanded=True):
                        ai_progress = st.progress(0)
                        ai_status = st.empty()
                        
                        ai_status.text("🧠 AI assistant analyzing multiple sources...")
                        ai_progress.progress(50)
                        
                        ai_result = contact_finder.search_with_ai(
                            company, website, country, provider, model, api_key, industry
                        )
                        
                        ai_progress.progress(100)
                        ai_status.text("✅ AI research completed!")
                        
                        if ai_result and not ai_result.startswith("❌"):
                            st.markdown("**🤖 AI Research Report:**")
                            st.markdown(ai_result)
                            
                            # Try to parse structured data
                            df = parse_markdown_table(ai_result)
                            if df is not None and not df.empty:
                                st.markdown("**📊 Structured Contact Data:**")
                                st.dataframe(df, use_container_width=True)
                                
                                # Extract emails from AI results
                                ai_emails = set()
                                for col in df.columns:
                                    if 'email' in col.lower():
                                        for email in df[col].dropna():
                                            if '@' in str(email) and '(estimated)' not in str(email):
                                                clean_email = str(email).strip().lower()
                                                if contact_finder.web_scraper.is_valid_email(clean_email):
                                                    ai_emails.add(clean_email)
                                
                                all_emails.update(ai_emails)
                                method_results['ai_research'] = ai_emails
                            
                            # Extract and display sources
                            citations = re.findall(r"\[([^\]]+)\]\((https?://[^\)]+)\)", ai_result)
                            if citations:
                                st.markdown("**📚 Research Sources:**")
                                for name, url in citations:
                                    st.markdown(f"• [{name}]({url})")
                                    research_sources.append({'name': name, 'url': url})
                        else:
                            st.error(f"AI research failed: {ai_result}")
                        
                        time.sleep(1)
                        ai_progress.empty()
                        ai_status.empty()
            
            # Method 5: Email Patterns
            if "📧 Email Patterns" in research_methods and include_patterns:
                current_method += 1
                status_text.text("📧 Generating intelligent email patterns...")
                overall_progress.progress(current_method / total_methods * 0.90)
                
                with st.expander("📧 Intelligent Email Pattern Suggestions", expanded=True):
                    patterns = generate_email_patterns(domain, country, industry)
                    
                    cols = st.columns(min(len(patterns), 3))
                    for i, (category, emails) in enumerate(patterns.items()):
                        with cols[i % len(cols)]:
                            st.markdown(f"**{category}:**")
                            for email in emails[:6]:
                                st.code(email)
            
            # Method 6: Manual Research Guide
            if "🔍 Manual Research Guide" in research_methods:
                with st.expander("🔍 Manual Research Strategy & Tips", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**🌐 Recommended Online Sources:**")
                        if country.lower() in ['germany', 'deutschland', 'de']:
                            suggestions = [
                                f"🇩🇪 **Impressum**: https://{domain}/impressum",
                                f"🔍 **Xing**: Search '{company}' employees",
                                "📋 **German Business Registry** (Handelsregister)",
                                "💼 **Local Chamber of Commerce**",
                                "🏢 **Bundesanzeiger** for official publications"
                            ]
                        else:
                            suggestions = [
                                f"🔍 **LinkedIn**: Company page and employee search",
                                f"📞 **Direct Call**: Main number for directory",
                                "📋 **Business Directories**: YellowPages, Yelp",
                                "💼 **Industry Associations**",
                                "🏢 **Chamber of Commerce** listings"
                            ]
                        
                        for suggestion in suggestions:
                            st.markdown(f"• {suggestion}")
                    
                    with col2:
                        st.markdown("**📞 Direct Outreach Strategies:**")
                        tips = [
                            "📞 **Call reception** for specific contacts",
                            "📧 **Email info@** requesting contact list",
                            "💬 **Use contact forms** on website",
                            "🤝 **Connect on professional networks**",
                            "📰 **Check recent press releases**",
                            "🎤 **Look for conference speakers**"
                        ]
                        
                        for tip in tips:
                            st.markdown(f"• {tip}")
            
            # Complete progress
            overall_progress.progress(1.0)
            status_text.text("✅ Comprehensive research completed!")
            
            time.sleep(1)
            overall_progress.empty()
            status_text.empty()
            
            # Display comprehensive results
            st.markdown("---")
            st.subheader("📊 Comprehensive Research Results")
            
            if all_emails or all_phones:
                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Emails", len(all_emails))
                col2.metric("Total Phones", len(all_phones))
                col3.metric("Methods Used", len([m for m in method_results.keys() if method_results[m]]))
                col4.metric("Total Contacts", len(all_emails) + len(all_phones))
                
                # Method comparison
                if len(method_results) > 1:
                    st.markdown("### 📈 Results by Research Method")
                    method_cols = st.columns(len(method_results))
                    
                    method_display_names = {
                        'whois': '📋 WHOIS',
                        'website_scraping': '🌍 Website',
                        'web_search': '🌐 Web Search',
                        'ai_research': '🤖 AI Research'
                    }
                    
                    for i, (method, emails) in enumerate(method_results.items()):
                        with method_cols[i]:
                            display_name = method_display_names.get(method, method)
                            st.metric(display_name, len(emails))
                
                # Categorized email results
                if all_emails:
                    st.markdown("### 📧 Email Contacts by Category")
                    categories = categorize_emails(list(all_emails))
                    
                    for category, emails in categories.items():
                        with st.expander(f"📧 {category.title()} Contacts ({len(emails)})", expanded=len(emails) <= 5):
                            for email in sorted(emails):
                                # Show which methods found each email
                                found_by = []
                                for method, method_emails in method_results.items():
                                    if email in method_emails:
                                        method_icon = {'whois': '📋', 'website_scraping': '🌍', 'web_search': '🌐', 'ai_research': '🤖'}.get(method, '🔍')
                                        found_by.append(method_icon)
                                
                                found_by_str = " ".join(found_by) if found_by else ""
                                st.markdown(f"• `{email}` {found_by_str}")
                
                # Phone numbers
                if all_phones:
                    st.markdown("### 📞 Phone Contacts")
                    with st.expander(f"📞 Phone Numbers ({len(all_phones)})", expanded=True):
                        for phone in sorted(all_phones):
                            st.code(phone)
                
                # Export functionality
                st.markdown("### 📤 Export Research Results")
                
                col1, col2, col3 = st.columns(3)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                filename_base = f"{company.lower().replace(' ', '_').replace(',', '')}_contacts_{timestamp}"
                
                # Prepare export data
                export_data = []
                
                if all_emails:
                    categories = categorize_emails(list(all_emails))
                    for category, emails in categories.items():
                        for email in emails:
                            found_by_methods = []
                            for method, method_emails in method_results.items():
                                if email in method_emails:
                                    found_by_methods.append(method)
                            
                            export_data.append({
                                "Contact": email,
                                "Type": "Email",
                                "Category": category.title(),
                                "Found_By": ", ".join(found_by_methods),
                                "Company": company,
                                "Website": website,
                                "Country": country,
                                "Industry": industry,
                                "Research_Date": datetime.now().strftime('%Y-%m-%d %H:%M'),
                                "Research_Methods": ", ".join(research_methods)
                            })
                
                if all_phones:
                    for phone in all_phones:
                        export_data.append({
                            "Contact": phone,
                            "Type": "Phone",
                            "Category": "General",
                            "Found_By": "multi-source",
                            "Company": company,
                            "Website": website,
                            "Country": country,
                            "Industry": industry,
                            "Research_Date": datetime.now().strftime('%Y-%m-%d %H:%M'),
                            "Research_Methods": ", ".join(research_methods)
                        })
                
                with col1:
                    # CSV export
                    if export_data and export_format in ["CSV", "Both"]:
                        df = pd.DataFrame(export_data)
                        csv_data = df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "⬇️ Download CSV",
                            data=csv_data,
                            file_name=f"{filename_base}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                
                with col2:
                    # JSON export
                    if export_format in ["JSON", "Both"]:
                        json_data = {
                            "research_metadata": {
                                "company": company,
                                "website": website,
                                "country": country,
                                "industry": industry,
                                "research_date": datetime.now().isoformat(),
                                "methods_used": research_methods,
                                "total_emails": len(all_emails),
                                "total_phones": len(all_phones)
                            },
                            "contacts": {
                                "emails": list(all_emails),
                                "phones": list(all_phones)
                            },
                            "method_results": {k: list(v) for k, v in method_results.items()},
                            "research_sources": research_sources
                        }
                        
                        st.download_button(
                            "⬇️ Download JSON",
                            data=json.dumps(json_data, indent=2).encode("utf-8"),
                            file_name=f"{filename_base}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                
                with col3:
                    # Text format for quick copying
                    all_contacts_text = []
                    if all_emails:
                        all_contacts_text.append("=== EMAILS ===")
                        all_contacts_text.extend(sorted(all_emails))
                        all_contacts_text.append("")
                    if all_phones:
                        all_contacts_text.append("=== PHONES ===")
                        all_contacts_text.extend(sorted(all_phones))
                    
                    if all_contacts_text:
                        st.text_area(
                            "📋 Quick Copy",
                            value='\n'.join(all_contacts_text),
                            height=200,
                            help="Copy all contacts for quick use"
                        )
            
            else:
                # No results found
                st.warning("🔍 No contact information found using the selected research methods")
                
                with st.expander("💡 Troubleshooting & Next Steps"):
                    st.markdown("""
                    **Possible reasons for no results:**
                    - Company may not publish contact information publicly
                    - Website may have strong anti-bot protection
                    - Company may be new or very small
                    - Contact information may be behind login walls
                    
                    **Recommended next steps:**
                    - Try different research methods or AI models
                    - Use the manual research guide above
                    - Contact the company directly via their website form
                    - Check industry-specific directories
                    - Look for the company on professional networks manually
                    """)
        
        except Exception as e:
            st.error(f"❌ Research error: {str(e)}")
            st.info("💡 Try reducing the number of pages to scrape or using different research methods")

if __name__ == "__main__":
    main()
