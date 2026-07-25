import os

def get_bool_env(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes", "on")

PROVIDER_SETTINGS = {
    "greenhouse": {"enabled": get_bool_env("ENABLE_GREENHOUSE", True)},
    "lever": {"enabled": get_bool_env("ENABLE_LEVER", True)},
    "ashby": {"enabled": get_bool_env("ENABLE_ASHBY", True)},
    "remote_ok": {"enabled": get_bool_env("ENABLE_REMOTE_OK", True)},
    "ycombinator": {"enabled": get_bool_env("ENABLE_YCOMBINATOR", False)},  # Disabled pending implementation
    "hacker_news": {"enabled": get_bool_env("ENABLE_HACKER_NEWS", True)},
    "hasjob": {"enabled": get_bool_env("ENABLE_HASJOB", True)},
    "company_careers": {"enabled": get_bool_env("ENABLE_COMPANY_CAREERS", True)},
}
