# Company Career Page Configurations
# To configure a direct company page, specify the adapter and options.
# Adapters supported: "json_ld", "rss", "generic_html"

COMPANY_CAREER_SITES = [
    {
        "company_name": "JSON-LD Example Company",
        "careers_url": "https://example.com/careers-jsonld",
        "adapter": "json_ld",
        "enabled": False,
    },
    {
        "company_name": "RSS Example Company",
        "careers_url": "https://example.com/careers/feed.xml",
        "adapter": "rss",
        "enabled": False,
    },
    {
        "company_name": "HTML Selector Example Company",
        "careers_url": "https://example.com/careers",
        "adapter": "generic_html",
        "enabled": False,
        "selectors": {
            "job_item_selector": "div.job-card",
            "title_selector": "h3.title",
            "location_selector": "span.location",
            "url_selector": "a.apply-link",
        },
    },
]
