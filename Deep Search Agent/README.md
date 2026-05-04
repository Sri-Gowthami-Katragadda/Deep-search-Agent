# 💹 Financial Deep Research Agent

A sophisticated multi-agent financial research system that conducts deep, multi-step research workflows similar to Claude's Deep Research mode — but specialized for IT and Pharma sectors.

## 🏗️ Architecture Overview

```
financial_research_agent/
├── main.py                         # Entry point & CLI interface
├── api/
│   └── app.py                      # FastAPI REST interface
├── agents/
│   ├── base_agent.py               # Abstract base for all sector agents
│   ├── it_agent.py                 # IT Sector specialized agent
│   ├── pharma_agent.py             # Pharma Sector specialized agent
│   └── router_agent.py             # Intelligent query routing agent
├── core/
│   ├── research_engine.py          # Core deep research loop engine
│   ├── report_generator.py         # Structured report generation
│   ├── financial_analyzer.py       # Financial metrics & calculations
│   └── rag_engine.py               # RAG for document intelligence
├── tools/
│   ├── tavily_search.py            # Tavily web search integration
│   ├── financial_api.py            # Financial data APIs
│   └── document_processor.py      # Annual report / PDF processing
├── utils/
│   ├── logger.py                   # Structured logging
│   ├── validators.py               # Input/output validation
│   └── helpers.py                  # Utility functions
├── config/
│   ├── settings.py                 # App configuration & env vars
│   └── sector_config.py            # Sector-specific configurations
├── prompts/
│   ├── system_prompts.py           # All LLM system prompts
│   └── templates.py                # Report & research templates
├── data/
│   ├── vector_db/                  # ChromaDB persistent storage
│   ├── reports/                    # Generated research reports
│   └── annual_reports/             # Uploaded financial documents
├── requirements.txt
├── .env.example
└── README.md
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run CLI
```bash
python main.py
```

### 4. Run API Server
```bash
uvicorn api.app:app --reload --port 8000
```

## 🔑 Required API Keys

| Key | Purpose | Get it at |
|-----|---------|-----------|
| `GROQ_API_KEY` | LLM reasoning (Llama 3.3 70B) | https://console.groq.com |
| `TAVILY_API_KEY` | Web search | https://tavily.com |

## 🧠 Research Flow

1. **Query Analysis** → Router agent classifies query and picks sector agents
2. **Research Planning** → Agent creates detailed research plan (shown to user)
3. **User Approval** → User reviews/modifies plan
4. **Deep Research Loop** → 5-20+ iterative searches, each informed by previous findings
5. **Synthesis** → All findings compiled into structured report
6. **Report Generation** → Markdown report saved to `data/reports/`

## 📊 Supported Query Types

- Company-specific analysis: _"Analyze TCS financials"_
- Sector trends: _"Emerging trends in Indian pharma"_
- Comparative studies: _"Compare Infosys vs Wipro"_
- Regulatory impact: _"Impact of PLI scheme on IT sector"_
- Investment research: _"Best IT stocks for 2025"_

## 🏭 Sector Agents

| Agent | Specialization |
|-------|---------------|
| IT Agent | Indian IT services, SaaS, cloud, AI/ML companies |
| Pharma Agent | Indian pharma, biosimilars, generic drugs, clinical trials |

## 📝 Sample Outputs

Reports are saved as Markdown files in `data/reports/` with structure:
- Executive Summary
- Market Overview
- Key Players Analysis
- Financial Metrics
- Trend Analysis
- Risk Factors
- Investment Outlook
