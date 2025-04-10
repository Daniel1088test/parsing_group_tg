# Модуль scripts для утиліт адміністрування та обслуговування

# Імпортуємо необхідні модулі для кращого доступу
try:
    from .direct_db_fix import fix_database_directly
except ImportError:
    pass

try:
    from .run_migrations import run_migrations
except ImportError:
    pass

# Make scripts directory a proper Python package 