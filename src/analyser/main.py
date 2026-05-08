from time import sleep
from fastapi import FastAPI, HTTPException, UploadFile
import uvicorn
import asyncio
import logging
import tempfile
import os
import shutil

from analysis import run as track_run

app = FastAPI()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

run_lock = asyncio.Lock()




@app.get("/healthz")
async def healthz():
    logger.info("hej hej")
    return "I'm alive!"

@app.post("/run")
async def run(file: UploadFile):
    if run_lock.locked():
        raise HTTPException(429, "Already running")

    if file.filename is None:
        raise HTTPException(400, "No filename")

    temp_dir = tempfile.mkdtemp(prefix="brage_analyser_upload_")
    temp_path = os.path.join(temp_dir, file.filename)

    logger.info("recieved file %s" % file.filename)
    async with run_lock:
        try:
            with open(temp_path, "wb") as f:
                while chunk := await file.read(1024 * 1024):
                    f.write(chunk)

            logger.info("start analysis")

            result = await asyncio.to_thread(track_run, temp_path)

            logger.info("finished analysis")

            return result

        except Exception as e:
            raise HTTPException(500, e.__str__())
        finally:
            await file.close()
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    logger.info("serving on port %s" % "3001")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3001,
        # access_log=False,
        reload=False,
        log_level="info",
        log_config=None,
    )
