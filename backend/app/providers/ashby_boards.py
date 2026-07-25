# Ashby Job Board Configurations
# To add a company:
# 1. Locate their Ashby job board name (e.g. "sentry" in https://jobs.ashbyhq.com/sentry)
# 2. Add below with job_board_name, company_name and enabled status.

ASHBY_BOARDS = [
    {
        "company_name": "Sentry",
        "job_board_name": "sentry",
        "enabled": True,
    },
    {
        "company_name": "Linear",
        "job_board_name": "linear",
        "enabled": True,
    },
    {
        "company_name": "Placeholder Company",
        "job_board_name": "placeholder-company",
        "enabled": False, # Disabled placeholder
    }
]
