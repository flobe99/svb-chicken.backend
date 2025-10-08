from sqlalchemy import create_engine

engine = create_engine("postgresql://neondb_owner:npg_7xhH5JrvlFLo@ep-nameless-pine-agu3hagk.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

try:
    with engine.connect() as conn:
        print("Verbindung erfolgreich!")
except Exception as e:
    print("Fehler:", e)
