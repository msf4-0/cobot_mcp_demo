from roboflow import Roboflow

ROBOFLOW_API = "pcc54MOylMq3KOEMQLpI"
rf = Roboflow(api_key=ROBOFLOW_API)
project = rf.workspace("reuben-if7ts").project("shapes-detection-fppqu")
version = project.version(3)
dataset = version.download("yolov8")