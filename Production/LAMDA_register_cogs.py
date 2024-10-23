import ee, os, datetime, json
from pprint import pprint
from google.auth.transport.requests import AuthorizedSession

ee.Authenticate()

ee_project = "gtac-lamda"

ee.Initialize(project=ee_project)
import geeViz.cloudStorageManagerLib as cml
import geeViz.assetManagerLib as aml


session = AuthorizedSession(ee.data.get_persistent_credentials().with_quota_project(ee_project))


###########################################################################################
# Set up buckets, collections, and see what already exists
import_endpoint = f"https://earthengine.googleapis.com/v1alpha/projects/{ee_project}/image:importExternal"

bucket = "lamda-products"
ee_folder = "projects/gtac-lamda/assets/lamda-outputs"
tdd_raw_collection = ee_folder + "/tdd_raw"
z_raw_collection = ee_folder + "/z_raw"

tdd_persistence_collection = ee_folder + "/tdd_persistence"
z_persistence_collection = ee_folder + "/z_persistence"


###########################################################################################
# Ingest functions
def ingest_raw_z(raw_z_tifs):
    for raw_z in raw_z_tifs:
        asset_basename = os.path.splitext(raw_z)[0]
        asset_name = f"{z_raw_collection}/{asset_basename}"

        print("Ingesting:", raw_z)
        yr = raw_z.split("_ay")[1].split("_")[0]
        startDay = raw_z.split("_jd")[1].split("-")[0]
        endDay = raw_z.split("_jd")[1].split("-")[1].split(".tif")[0]
        startDate = datetime.datetime.strptime(f"{yr} {startDay}", "%Y %j").strftime("%Y-%m-%dT%H:%M:%SZ")
        endDate = datetime.datetime.strptime(f"{yr} {endDay}", "%Y %j").strftime("%Y-%m-%dT%H:%M:%SZ")

        uri = f"gs://{bucket}/{raw_z}"
        print(asset_name, uri)
        request = {
            "imageManifest": {
                "name": asset_name,
                "tilesets": [{"id": "0", "sources": {"uris": [uri]}}],
                "bands": [{"id": "LAMDA_Z", "tilesetId": "0", "tilesetBandIndex": 0}],
                "startTime": startDate,
                "endTime": endDate,
            },
        }

        pprint(request)

        response = session.post(url=import_endpoint, data=json.dumps(request))

        pprint(json.loads(response.content))


###########################################
def ingest_raw_tdd(raw_tdd_tifs):
    for raw_tdd in raw_tdd_tifs:
        asset_basename = os.path.splitext(raw_tdd)[0]
        asset_name = f"{tdd_raw_collection}/{asset_basename}"

        print("Ingesting:", raw_tdd)
        yr = raw_tdd.split("_yrs")[1].split("-")[1].split("_")[0]
        print(yr)
        startDay = raw_tdd.split("_jd")[1].split("-")[0]
        endDay = raw_tdd.split("_jd")[1].split("-")[1].split(".tif")[0]
        print(startDay, endDay)
        startDate = datetime.datetime.strptime(f"{yr} {startDay}", "%Y %j").strftime("%Y-%m-%dT%H:%M:%SZ")
        endDate = datetime.datetime.strptime(f"{yr} {endDay}", "%Y %j").strftime("%Y-%m-%dT%H:%M:%SZ")

        uri = f"gs://{bucket}/{raw_tdd}"
        # print(asset_name,uri)
        request = {
            "imageManifest": {
                "name": asset_name,
                "tilesets": [{"id": "0", "sources": {"uris": [uri]}}],
                "bands": [{"id": "LAMDA_TDD", "tilesetId": "0", "tilesetBandIndex": 0}],
                "startTime": startDate,
                "endTime": endDate,
            },
        }

        response = session.post(url=import_endpoint, data=json.dumps(request))

        pprint(json.loads(response.content))


###########################################
def ingest_persistence_z(persistence_z_tifs):
    for persistence_z in persistence_z_tifs:
        asset_basename = os.path.splitext(persistence_z)[0]
        asset_name = f"{z_persistence_collection}/{asset_basename}"

        print("Ingesting:", persistence_z)
        yr = persistence_z.split("_ay")[1].split("_")[0]
        startDay = persistence_z.split("_jds")[1].split("-")[-1].split("_")[0]
        endDay = startDay

        startDate = datetime.datetime.strptime(f"{yr} {startDay}", "%Y %j").strftime("%Y-%m-%dT%H:%M:%SZ")
        endDate = datetime.datetime.strptime(f"{yr} {endDay}", "%Y %j").strftime("%Y-%m-%dT%H:%M:%SZ")

        uri = f"gs://{bucket}/{persistence_z}"
        print(asset_name, uri)
        request = {
            "imageManifest": {
                "name": asset_name,
                "tilesets": [{"id": "0", "sources": {"uris": [uri]}}],
                "bands": [{"id": "LAMDA_Z", "tilesetId": "0", "tilesetBandIndex": 0}],
                "startTime": startDate,
                "endTime": endDate,
            },
        }

        pprint(request)

        response = session.post(url=import_endpoint, data=json.dumps(request))

        pprint(json.loads(response.content))


###########################################
def ingest_persistence_tdd(persistence_tdd_tifs):
    for persistence_tdd in persistence_tdd_tifs:
        asset_basename = os.path.splitext(persistence_tdd)[0]
        asset_name = f"{tdd_persistence_collection}/{asset_basename}"

        print("Ingesting:", persistence_tdd)
        yr = persistence_tdd.split("_yrs")[1].split("-")[1].split("_")[0]
        startDay = persistence_tdd.split("_jds")[1].split("-")[-1].split("_")[0]
        endDay = startDay

        startDate = datetime.datetime.strptime(f"{yr} {startDay}", "%Y %j").strftime("%Y-%m-%dT%H:%M:%SZ")
        endDate = datetime.datetime.strptime(f"{yr} {endDay}", "%Y %j").strftime("%Y-%m-%dT%H:%M:%SZ")

        uri = f"gs://{bucket}/{persistence_tdd}"

        request = {
            "imageManifest": {
                "name": asset_name,
                "tilesets": [{"id": "0", "sources": {"uris": [uri]}}],
                "bands": [{"id": "LAMDA_TDD", "tilesetId": "0", "tilesetBandIndex": 0}],
                "startTime": startDate,
                "endTime": endDate,
            },
        }

        response = session.post(url=import_endpoint, data=json.dumps(request))

        pprint(json.loads(response.content))


###############################################
def ingest_lamda():

    # Create the image collections if they don't exist
    aml.create_asset(tdd_raw_collection, ee.data.ASSET_TYPE_IMAGE_COLL)
    aml.create_asset(z_raw_collection, ee.data.ASSET_TYPE_IMAGE_COLL)
    aml.create_asset(tdd_persistence_collection, ee.data.ASSET_TYPE_IMAGE_COLL)
    aml.create_asset(z_persistence_collection, ee.data.ASSET_TYPE_IMAGE_COLL)

    # Find existing assets
    existing_raw_z = ee.ImageCollection(z_raw_collection).aggregate_histogram("system:index").keys().getInfo()
    existing_raw_tdd = ee.ImageCollection(tdd_raw_collection).aggregate_histogram("system:index").keys().getInfo()
    existing_persistence_z = ee.ImageCollection(z_persistence_collection).aggregate_histogram("system:index").keys().getInfo()
    existing_persistence_tdd = ee.ImageCollection(tdd_persistence_collection).aggregate_histogram("system:index").keys().getInfo()

    # Filter down cogs from gcs
    all_files = cml.list_files(bucket)
    tifs = [f for f in all_files if os.path.splitext(f)[1] == ".tif"]

    raw_tifs = [t for t in tifs if t.split("_")[-1].find("jd") > -1]
    persistence_tifs = [t for t in tifs if t.split("_")[-1].find("persistence") > -1]

    raw_z_tifs = [t for t in raw_tifs if t.find("_Z_") > -1 and os.path.splitext(t)[0] not in existing_raw_z]
    raw_tdd_tifs = [t for t in raw_tifs if t.find("_TDD_") > -1 and os.path.splitext(t)[0] not in existing_raw_tdd]

    persistence_z_tifs = [t for t in persistence_tifs if t.find("_Z_") > -1 and os.path.splitext(t)[0] not in existing_persistence_z]
    persistence_tdd_tifs = [t for t in persistence_tifs if t.find("_TDD_") > -1 and os.path.splitext(t)[0] not in existing_persistence_tdd]

    print(raw_z_tifs, raw_tdd_tifs, persistence_z_tifs, persistence_tdd_tifs)
    ingest_raw_z(raw_z_tifs)
    ingest_raw_tdd(raw_tdd_tifs)
    ingest_persistence_z(persistence_z_tifs)
    ingest_persistence_tdd(persistence_tdd_tifs)


#########################################################################################
if __name__ == "__main__":
    ingest_lamda()
