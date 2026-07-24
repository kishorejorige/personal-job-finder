# Greenhouse Board Configurations
# To add a company:
# 1. Open their Greenhouse-hosted careers URL, e.g., https://boards.greenhouse.io/stripe
# 2. Extract the board token (e.g. "stripe")
# 3. Add to the list below: {"company_name": "Stripe", "board_token": "stripe"}
# 4. Restart the backend and run "Fetch Greenhouse Jobs" from the frontend.

GREENHOUSE_BOARDS = [
    {
        "company_name": "Figma",
        "board_token": "figma",
    },
    {
        "company_name": "Stripe",
        "board_token": "stripe",
    },
    {
        "company_name": "Vimeo",
        "board_token": "vimeo",
    },
    {
        "company_name": "Docker",
        "board_token": "docker",
    }
]
