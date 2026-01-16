from models import Base, engine

print("Creating database tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("Success! The 'expenses' table has been created in PostgreSQL.")
except Exception as e:
    print(f"An error occurred: {e}")