"""
config/sector_config.py
───────────────────────
Sector-specific knowledge, keywords, KPIs, and search strategies.
Adding a new sector = adding a new entry to SECTOR_CONFIGS.
"""

from dataclasses import dataclass, field
from typing import List, Dict

# dataclass is python class that just holds data , no methods needed 
# this defines the blueprint for a sectors configurations
@dataclass
class SectorConfig:
    name: str
    display_name: str
    description: str
    keywords: List[str]                  # Routing keywords
    key_companies: List[str]             # Major players to track
    key_metrics: List[str]               # Sector-specific KPIs
    search_domains: List[str]            # Preferred news/data sources
    sub_sectors: List[str]               # Sub-categories within sector
    regulatory_bodies: List[str]         # Relevant regulators
    base_search_terms: List[str]         # Initial broad search terms


# ── IT SECTOR ─────────────────────────────────────────────────────────────────
# hardcoded knowledge about IT sector , keywords are used for routing 
# key_metrics appear in prompts to guide the LLM .
IT_CONFIG = SectorConfig(
    name="it",
    display_name="Indian IT Services & Technology",
    description="Covers Indian IT services companies, software exports, cloud computing, AI/ML, and digital transformation.",
    keywords=[
        "IT", "information technology", "software", "tech", "TCS", "Infosys",
        "Wipro", "HCL", "Tech Mahindra", "cloud", "AI", "SaaS", "digital",
        "outsourcing", "BPO", "cybersecurity", "data center", "IT services",
        "NASSCOM", "Cognizant", "Mphasis", "LTIMindtree", "Persistent",
    ],
    key_companies=[
        "TCS", "Infosys", "Wipro", "HCL Technologies", "Tech Mahindra",
        "LTIMindtree", "Mphasis", "Persistent Systems", "Coforge",
        "Hexaware", "KPIT Technologies", "Tata Elxsi",
    ],
    key_metrics=[
        "Revenue Growth Rate", "EBIT Margin", "Attrition Rate",
        "Deal TCV (Total Contract Value)", "Revenue per Employee",
        "Headcount Growth", "Digital Revenue Mix", "Utilization Rate",
        "Days Sales Outstanding (DSO)", "Free Cash Flow Conversion",
    ],
    search_domains=[
        "economictimes.com", "livemint.com", "moneycontrol.com",
        "nasscom.in", "techcrunch.com", "bseindia.com", "nseindia.com",
    ],
    sub_sectors=[
        "IT Services", "Product Companies", "SaaS", "IT Infrastructure",
        "BPO/KPO", "Engineering Services", "Cybersecurity", "Fintech",
    ],
    regulatory_bodies=[
        "NASSCOM", "Ministry of Electronics and IT (MeitY)", "RBI (for fintech)",
        "SEBI", "CERT-In",
    ],
    base_search_terms=[
        "Indian IT sector outlook 2025",
        "IT services India revenue growth",
        "Indian tech companies quarterly results",
    ],
)

# ── PHARMA SECTOR ─────────────────────────────────────────────────────────────
PHARMA_CONFIG = SectorConfig(
    name="pharma",
    display_name="Indian Pharmaceutical & Healthcare",
    description="Covers Indian pharmaceutical companies, drug manufacturing, biosimilars, generics, CDMO, and healthcare.",
    keywords=[
        "pharma", "pharmaceutical", "drug", "medicine", "healthcare", "biotech",
        "biosimilar", "generic", "API", "CDMO", "Sun Pharma", "Dr Reddy",
        "Cipla", "Lupin", "Divi's", "Aurobindo", "USFDA", "clinical trial",
        "vaccine", "biologics", "oncology", "formulation", "Active Pharmaceutical Ingredient",
    ],
    key_companies=[
        "Sun Pharmaceutical", "Dr. Reddy's Laboratories", "Cipla",
        "Lupin", "Aurobindo Pharma", "Divi's Laboratories",
        "Biocon", "Alkem Laboratories", "Torrent Pharmaceuticals",
        "Glenmark Pharmaceuticals", "Abbott India", "Pfizer India",
    ],
    key_metrics=[
        "R&D Spend as % of Revenue", "US FDA Approval Rate",
        "ANDA Filings", "Domestic vs Export Revenue Split",
        "API vs Formulation Revenue", "EBITDA Margin",
        "Biosimilar Pipeline Value", "CDMO Revenue Growth",
        "Form 483 Observations", "Capex on Manufacturing",
    ],
    search_domains=[
        "pharmabiz.com", "drugtoday.com", "fiercepharma.com",
        "fdanews.com", "economictimes.com", "livemint.com",
        "clinicaltrials.gov", "bseindia.com",
    ],
    sub_sectors=[
        "Generic Drugs", "API Manufacturing", "Biosimilars", "CDMO",
        "Vaccine Manufacturing", "OTC Products", "Medical Devices",
        "Specialty Pharma", "Hospital Chains",
    ],
    regulatory_bodies=[
        "USFDA", "CDSCO", "EMA", "WHO-GMP", "DCGI",
        "Ministry of Chemicals and Fertilizers",
    ],
    base_search_terms=[
        "Indian pharmaceutical sector analysis 2025",
        "India pharma exports generics market",
        "USFDA approvals Indian pharma companies",
    ],
)

# ── SECTOR REGISTRY ───────────────────────────────────────────────────────────
# registry dictionary , adding a new sector is adding a one line here 
SECTOR_CONFIGS: Dict[str, SectorConfig] = {
    "it": IT_CONFIG,
    "pharma": PHARMA_CONFIG,
    # Future sectors can be added here:
    # "banking": BANKING_CONFIG,
}


def get_sector_config(sector_name: str) -> SectorConfig:
    """Get config for a sector by name."""
    config = SECTOR_CONFIGS.get(sector_name.lower())
    if not config:
        raise ValueError(f"Unknown sector: {sector_name}. Available: {list(SECTOR_CONFIGS.keys())}")
    return config


def get_all_keywords() -> Dict[str, List[str]]:
    """Returns all keywords mapped to their sector for routing."""
    return {
        sector: config.keywords
        for sector, config in SECTOR_CONFIGS.items()
    }
