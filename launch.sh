#!/bin/bash

# Currently so don't have to rebuild docker machines; see
# https://github.com/dask/dask-docker/pull/108

export SALMON_NPROC=$(getconf _NPROCESSORS_ONLN)

# chose nthreads=1 because best practice [1]
# [1]: https://docs.dask.org/en/latest/array-best-practices.html#avoid-oversubscribing-threads
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

dask-scheduler --host 127.0.0.2 --port 8786 --dashboard-address :8787 &
dask-worker --nprocs $SALMON_NPROC --nthreads 1 127.0.0.2:8786 &

if [ $SALMON_DEBUG ]
then
    # export SALMON_DEBUG=1 or export SALMON_DEBUG=0
    export LOG_LEVEL=INFO
    echo "Launching uvicorn..."
    uvicorn salmon:app_algs --reload --reload-dir salmon --port 8400 --host 0.0.0.0 &
    sleep 1
    uvicorn salmon:app --reload --reload-dir salmon --reload-dir templates --port 8421 --host 0.0.0.0
else
    # unset SALMON_DEBUG if already set in enviroment
    #
    # Use shared memory for Gunicorn; apparelty can block on AWS
    # [1]:https://pythonspeed.com/articles/gunicorn-in-docker/
    #
    # Set timeout=90 so Gunicorn checks less frequently.
    # Use preload to reduce startup time
    # Use 2 threads to heartbeat gets sent more often
    echo "Launching gunicorn..."
    export LOG_LEVEL=WARNING

    ## Use uvicorn instead of gunicorn because FastAPI's background tasks are threads
    ## in uvicorn, not processes.
    # gunicorn --preload --worker-tmp-dir /dev/shm --threads 2 --timeout 90 -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8400 salmon:app_algs &
    uvicorn salmon:app_algs --port 8400 --host 0.0.0.0 &
    sleep 1
    gunicorn --worker-tmp-dir /dev/shm --threads 2 --timeout 90 -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8421 salmon:app
fi
