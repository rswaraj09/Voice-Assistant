"""
Historical bootstrap / migration notes for `nora.db`.

This file used to contain ad-hoc scripts for schema setup and a few
one-off updates (e.g. rewriting the WhatsApp path). Schema creation is
now handled inside each feature module's initialiser — see
`engine.modes.init_mode_tables`, `engine.news_aggregator.init_news_tables`,
`engine.avatar_generator.init_avatar_tables`.

Keep this file so imports elsewhere don't break, but do not put live
statements here — running `python engine/db.py` should be a no-op.
"""
