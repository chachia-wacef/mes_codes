#!/bin/bash
set -ex

# 1h d'inactivité
IDLE_TIME=3600

cat > /home/ec2-user/SageMaker/autostop.py <<'PYEOF'
import requests, getopt, sys, json, boto3, urllib3
from datetime import datetime
from zoneinfo import ZoneInfo

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Paramètres ---
time = None
port = '8443'
ignore_connections = False
START_HOUR_LOCAL = 18                  # n'arrêter qu'à partir de 18h
TZ = ZoneInfo("Europe/Paris")          # gère été/hiver automatiquement

opts, args = getopt.getopt(sys.argv[1:], "t:p:c", ["time=", "port=", "ignore-connections"])
for opt, arg in opts:
    if opt in ("-t", "--time"):
        time = int(arg)
    if opt in ("-p", "--port"):
        port = str(arg)
    if opt in ("-c", "--ignore-connections"):
        ignore_connections = True

if time is None:
    print("Missing '-t' or '--time'")
    sys.exit(2)

# --- Garde-fou horaire : rien avant 18h, heure de Paris ---
now_local = datetime.now(TZ)
if now_local.hour < START_HOUR_LOCAL:
    print(f"Il est {now_local:%H:%M} (Europe/Paris), avant {START_HOUR_LOCAL}h : pas d'arrêt.")
    sys.exit(0)

def is_idle(last_activity):
    last_activity = datetime.strptime(last_activity, "%Y-%m-%dT%H:%M:%S.%fz")
    return (datetime.now() - last_activity).total_seconds() > time

def get_notebook_name():
    with open('/opt/ml/metadata/resource-metadata.json') as f:
        return json.load(f)['ResourceName']

idle = True
response = requests.get('https://localhost:'+port+'/api/sessions', verify=False)
data = response.json()

if len(data) > 0:
    for notebook in data:
        if notebook['kernel']['execution_state'] != 'idle':
            idle = False
            break
        if not ignore_connections and notebook['kernel']['connections'] != 0:
            idle = False
            break
        if not is_idle(notebook['kernel']['last_activity']):
            idle = False
            break
else:
    # Aucune session ouverte : on se base sur la dernière modif de l'instance
    client = boto3.client('sagemaker')
    desc = client.describe_notebook_instance(NotebookInstanceName=get_notebook_name())
    last = desc['LastModifiedTime'].replace(tzinfo=None)
    if (datetime.utcnow() - last).total_seconds() < time:
        idle = False

if idle:
    print("Inactif > 1h et après 18h -> arrêt de l'instance.")
    boto3.client('sagemaker').stop_notebook_instance(NotebookInstanceName=get_notebook_name())
else:
    print("Instance active : on ne fait rien.")
PYEOF

# Python de l'env système Amazon Linux 2 (contient boto3)
PYTHON_DIR='/home/ec2-user/anaconda3/envs/JupyterSystemEnv/bin/python'

# Cron toutes les 5 min
(crontab -l 2>/dev/null; echo "*/5 * * * * $PYTHON_DIR /home/ec2-user/SageMaker/autostop.py --time $IDLE_TIME --ignore-connections >> /var/log/jupyter.log 2>&1") | crontab -

echo "Lifecycle auto-stop (Amazon Linux 2 / JL4, après 18h, 1h d'inactivité) installée."
