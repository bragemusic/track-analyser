from time import sleep
from fastapi import FastAPI, HTTPException, UploadFile
import uvicorn
import asyncio
import logging
import tempfile
import os
import shutil
import structlog

from analysis import run as track_run

app = FastAPI()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso", key="time"),
        structlog.processors.add_log_level,
        structlog.processors.EventRenamer("msg"),
        structlog.contextvars.merge_contextvars,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

run_lock = asyncio.Lock()




@app.get("/healthz")
async def healthz():
    return "I'm alive!"

@app.post("/run")
async def run(file: UploadFile):
    if run_lock.locked():
        raise HTTPException(429, "Already running")

    if file.filename is None:
        raise HTTPException(400, "No filename")

    filename = os.path.basename(file.filename)
    temp_dir = tempfile.mkdtemp(prefix="brage_analyser_upload_")
    temp_path = os.path.join(temp_dir, filename)

    logger.info("recieved file %s" % filename)
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
            logger.error("could not analyse file", filename=filename, error=e.__str__())
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
