"""python -m app → start the product shell."""

from app.envload import load_dotenv

load_dotenv()

from app.server import main

if __name__ == "__main__":
    main()
