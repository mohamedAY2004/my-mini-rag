## Write your configuration:

```bash
cp alembic.ini.example alembic.ini
```

- Edit the `alembic.ini` file to match your database configuration (`sqlalchemy.url`).

## Run the migrations:
- Modify tables in the `schemas` folder as you like for almebic to include them in the migration the table must inherit from the `SQLAlchemyBase`.
- Create a the file for migration:
```bash
alembic revision --autogenerate -m "I did ...."
```
- Run the migrations:
```bash
alembic upgrade head
```
