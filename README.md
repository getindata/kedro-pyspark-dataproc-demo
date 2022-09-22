## Scenario 2: Serverless Spark / Dataproc Batches

### Environment setup
Kedro PySpark / Iris
https://github.com/quantumblacklabs/kedro-starter-pyspark-iris

```
# Create a directory for your project
mkdir workshop

# Install the virtualenv package  
pip install virtualenv 

# Create the virtualenv with the specific Python version
virtualenv workshop-env --python=python3.9  

# Activate the virtualenv
source workshop-env/bin/activate

# Go to the working directory
cd workshop
```

`conda deactivate` if needed.

### Install Kedro
Note: remember use Kedro in the specific version: `kedro==0.18.2`
```
# Install the Kedro Python package in the virtual environment
pip install 'kedro==0.18.2'
```


### Create new project
```
kedro new --starter=pyspark-iris
```

### Install project dependencies
Please install the project dependencies, defined in the `src/requirements.txt` file.  
Note: in the future you’ll add new Python packages there.

```  
# Make sure you’re in your project’s main folder
cd iris

# Add the following dependencies in src/requirements.txt
kedro-docker==0.3.0
pyspark==3.2.2

# Install project dependencies
pip install -r src/requirements.txt
```

### Run pipeline locally
```
kedro run
# exit with error
```

### Modify pipeline

Add `src/entrypoint.py`  script for pipeline startup on Dataproc Batches

```
import os
from kedro.framework import cli

os.chdir('/home/kedro')
cli.main()
```

### Prepare Docker image

Initialize plugin. It will add `Dockerfile` and `.dockerignore` files:
```
kedro docker init
```

Adjust `.dockerignore `
```
# Add this line to include the input file inside Docker container
# In other scenarios it will be optional if you'll read input data from external storage, i.e. GCS

!data/01_raw
```

Adjust `Dockerfile `

```
ARG BASE_IMAGE=python:3.9-buster

FROM $BASE_IMAGE

# overwrite default Dataproc PYSPARK_PYTHON path
ENV PYSPARK_PYTHON /usr/local/bin/python

ENV SPARK_EXTRA_CLASSPATH /usr/local/lib/python3.9/site-packages/pyspark/jars/*


# install project requirements
COPY src/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm -f /tmp/requirements.txt

# (Required) Install utilities required by Spark scripts.
RUN apt update && apt install -y procps tini openjdk-11-jre-headless

# add kedro user
ARG KEDRO_UID=999
ARG KEDRO_GID=0

RUN groupadd -f -g ${KEDRO_GID} kedro_group && \

useradd -d /home/kedro -s /bin/bash -g ${KEDRO_GID} -u ${KEDRO_UID} kedro

# (Required) Create the 'spark' group/user.
# The GID and UID must be 1099. Home directory is required.
RUN groupadd -g 1099 spark
RUN useradd -u 1099 -g 1099 -d /home/spark -m spark
#USER spark

# copy the whole project except what is in .dockerignore
WORKDIR /home/kedro

COPY . .

RUN chown -R kedro:${KEDRO_GID} /home/kedro

USER kedro

RUN chmod -R a+w /home/kedro

EXPOSE 8888

CMD ["kedro", "run"]
```

Build docker container

```
docker build \
	-t gcr.io/gid-ml-ops-sandbox/pyspark-tutorial-mb:20220920105 \
	.

docker push gcr.io/gid-ml-ops-sandbox/pyspark-tutorial-mb:20220920105
```

### Create Service Account on GCP project for the pipeline execution
Required role: `dataproc\worker`
```
kedro-pyspark-dataproc@gid-ml-ops-sandbox.iam.gserviceaccount.com
```

### Schedule pipeline for execution  on Dataproc Batches / Serverless Spark
```
gcloud dataproc batches submit pyspark file:///home/kedro/src/entrypoint.py \
    --project gid-ml-ops-sandbox \
    --region=europe-west1\
    --container-image=gcr.io/gid-ml-ops-sandbox/pyspark-tutorial-mb:20220920105 \
    --service-account kedro-pyspark-dataproc@gid-ml-ops-sandbox.iam.gserviceaccount.com \
    --properties spark.dynamicAllocation.minExecutors=2,spark.dynamicAllocation.maxExecutors=2 -- \
    run 
```

## Troubleshooting
Resources
https://cloud.google.com/dataproc-serverless/docs/concepts/properties#custom_spark_properties

#### Checklist
[+] service account with dataproc/worker permissions  
[+] add `src/entrypoint.py`  
[+] instal dependencies in Docker `procps tini openjdk-11-jre-headless`  
[+] set `ENV PYSPARK_PYTHON /usr/local/bin/python`  

[-] (optional) subnet z otwarciem portów na komunikację pod-pod  
[-] (optional) custom Kedro context  

[+] set PySpark version 3.2.2 (default is 3.3.0 which is incompatible https://cloud.google.com/dataproc-serverless/docs/concepts/versions/spark-runtime-versions)  
[+] Spark user in dockerfile (?)  

#### Adjust the pipeline code
[+] (optional) Upload file to GCS, adjust Data Catalog for input data
[+] change datasets to MemoryDatasets
[+] `src/iris/nodes.py` split_data -> toPandas()
[+] remove engine pandas/pyspark from `src/iris/pipeline.py`

#### To save files on GCS
i.e. export the model by GCS path in DataCatalog
```
gcsfs==2022.1.0 # see fsspec version / to save files on GCS
```