# Agronomist SDK Test Fixtures

Configuration and fixtures for testing the [agronomist-sdk](https://github.com/Local-Grown-Salads/agronomist-sdk).

## Files

- `init.sql` - PostgreSQL schema and seed data for test database
- `fixtures.py` - Hand-rolled fixture setup/teardown

## fixtures.py

```python
def create():
    """Create and return the fixture instance."""
    from lgs_agronomist_sdk import Client

    return Client()


def teardown(fixture):
    """Clean up after test."""
    fixture.close()
```

Customize `create()` to:
- Set environment variables
- Mock external services
- Seed additional test data
- Configure the Client

## Database Schema

The service requires these views in the `api` schema:

| View | Used By | Key Columns |
|------|---------|-------------|
| `fetch_product_assembly_db_view` | `assembly.get_product_by()` | `product_id` |
| `fetch_inspector_db_view` | `inspector.get_*()` | `grow_formula_id`, `day_number`, `time_segment_id` |

## Test Data

### Products (assembly)
| product_id | product_name |
|------------|--------------|
| TEST-001 | Test Product 1 |
| TEST-002 | Test Product 2 |
| TEST-003 | Test Product 3 |

### Inspector Configs
| grow_formula_id | day_number | time_segment_id |
|-----------------|------------|-----------------|
| FORMULA-001 | 1 | MORNING |
| FORMULA-001 | 1 | AFTERNOON |
| FORMULA-001 | 1 | NIGHT |

## Spreadsheet Example

| test_name | function | input | expected | status |
|-----------|----------|-------|----------|--------|
| get_product | assembly.get_product_by | "TEST-001" | | |
