"""Skrip entrypoint untuk menjalankan server SUKU-Monitor dengan uvicorn."""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"Memulai SUKU-Monitor di http://0.0.0.0:{settings.app_port}...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.app_port, reload=False)
