# Vulture whitelist — silences known-good "unused" for FastAPI/SQLAlchemy/Pydantic/pytest stacks
#
# Usage during /review STEP 4.8:
#   cp .vulture_whitelist.py.template .vulture_whitelist.py  # one-time, customize per project
#   uv run vulture src/ .vulture_whitelist.py --min-confidence 80
#
# OR equivalent [tool.vulture] block in pyproject.toml — see
# .claude/rules/references/static-analysis-tier2.md
#
# This file mimics usage patterns so vulture sees these as referenced.
# Remove sections not relevant to your project.

# ============================================================
# FastAPI — route handlers used via decorators
# ============================================================
_.app
_.router
_.lifespan
_.startup
_.shutdown

# ============================================================
# SQLAlchemy — models used via ORM registry / metadata
# ============================================================
_.Base
_.metadata
_.__tablename__
_.__table_args__
_.relationship

# ============================================================
# Pydantic — classes used via FastAPI type hints
# ============================================================
_.Config
_.model_config
_.BaseModel

# ============================================================
# pytest — fixtures and test functions invoked by collector
# ============================================================
_.fixture
_.parametrize
_.conftest
_.pytest_collection_modifyitems
_.pytest_configure

# ============================================================
# Project-specific — add your own here
# ============================================================
# Example: a CLI command auto-discovered via entry_points
# _.my_cli_command

# Example: a callback registered via signal/event system
# _.on_user_created
