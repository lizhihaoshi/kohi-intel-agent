# ☕️ Kohi Intel Agent (Kohi-Intel)

An AI-driven market intelligence agent designed to monitor the Japanese specialty coffee landscape. It automates competitor tracking, distills business insights, and generates poetic, "airy" social media copy.

## ✨ Features

- **Multi-Source Intelligence:** Automatically tracks 50+ premium coffee brands via Google News RSS, PR Times (Japan), and DuckDuckGo.
- **AI Distillation:** Powered by Gemini 2.0 Flash to filter noise and extract high-value business moves (new openings, limited collaborations, menu updates).
- **Poetic Copywriting:** Generates "Airy Style" (inspired by Yataro Matsuura) Instagram captions in both Japanese and Chinese.
- **Automated Reporting:** Generates clean Markdown daily reports and comprehensive weekly strategic summaries.

## 🛠️ Tech Stack

- **Core:** Python 3 (Standard Libraries only)
- **AI Engine:** Google Gemini AI (Generative Language API)
- **Data Sourcing:** RSS Parsing, Regex-based Web Scraping, Concurrent Fetching

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone [https://github.com/lizhihaoshi/kohi-intel-agent.git](https://github.com/lizhihaoshi/kohi-intel-agent.git)
cd kohi-intel-agent
2. Set up your Environment Variable

To keep your credentials secure, the agent reads the API key from your environment:

Bash
export GEMINI_API_KEY='your_gemini_api_key_here'
3. Run the Agent

Bash
python3 coffee_agent.py
The daily intelligence report will be generated in the /reports directory.

📂 Project Structure
coffee_agent.py: The main engine.

competitors.json: Curated list of 50+ Japanese coffee brands & vibes.

reports/: Storage for daily/weekly intelligence assets.

Created as part of the Lagomnoa Lab project — focusing on the intersection of coffee culture, healing economy, and AI efficiency.
