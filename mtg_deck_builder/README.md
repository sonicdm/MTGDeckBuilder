# mtg_deck_builder

...existing content...

## Database Setup

The `mtg_deck_builder.db.setup` module provides utilities for initializing the database and ensuring all required tables exist.

### `setup_database`

```python
from mtg_deck_builder.db.setup import setup_database

engine = setup_database("sqlite:///path/to/your.db")
```

- **Purpose:**  
  Ensures all tables defined in the ORM models are present in the database.  
  It is safe to call multiple times; existing data will not be dropped or overwritten.

- **Arguments:**  
  - `db_url`: SQLAlchemy database URL (e.g., `'sqlite:///path/to/db.sqlite'`)
  - `poolclass`: (optional) SQLAlchemy pool class
  - `connect_args`: (optional) SQLAlchemy connect arguments

- **Returns:**  
  A SQLAlchemy `Engine` object connected to the database.

- **Safety:**  
  This function only creates missing tables. It does **not** drop or modify existing tables or data.

...existing content...
