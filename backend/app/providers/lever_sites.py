# Lever Site Configurations
# To add a company:
# 1. Locate their Lever careers board slug (e.g. "figma" in https://jobs.lever.co/figma)
# 2. Add below with site_name, company_name, region ("global" or "eu") and enabled status.

LEVER_SITES = [
    {
        "company_name": "Figma",
        "site_name": "figma",
        "region": "global",
        "enabled": True,
    },
    {
        "company_name": "Reddit",
        "site_name": "reddit",
        "region": "global",
        "enabled": True,
    },
    {
        "company_name": "Vercel",
        "site_name": "vercel",
        "region": "global",
        "enabled": True,
    },
    {
        "company_name": "Example Company EU",
        "site_name": "example-company-eu",
        "region": "eu",
        "enabled": False,  # Disabled placeholder for EU region site
    },
]
