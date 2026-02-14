import os
import boto3

from botocore.config import Config
from flask import Flask, render_template, request, jsonify
from flask_caching import Cache

from src.models import Monitor, MonitoringScope
from peewee import fn
from typing import Dict, List

app = Flask(__name__, static_folder='static', template_folder='templates')

app.config['CACHE_TYPE'] = 'SimpleCache'  # Use a simple in-memory cache
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # Cache timeout in seconds

cache = Cache(app)

s3_client = boto3.resource(
    's3',
    endpoint_url=os.environ["S3_ENDPOINT"],
    aws_access_key_id=os.environ["S3_KEY_ID"],
    aws_secret_access_key=os.environ["S3_SECRET_KEY"],
    config=Config(signature_version='s3v4'),
    verify=False
)

bucket = s3_client.Bucket('monitoring-storage')


def get_monitor_thumb(monitor_id: str) -> str:
    shinobi_host = "shinobi.home"
    shinobi_key = "kFZ0nGq478IEkJO1CQL5g4913fys8o"
    shinobi_endpoint = f"http://{shinobi_host}/{shinobi_key}"

    monitor_group_id = "0ZOGYRpKx2"
    return f"{shinobi_endpoint}/jpeg/{monitor_group_id}/{monitor_id}/s.jpg"


@app.route("/api/v1/monitors")
def get_monitors():
    monitors = Monitor.select()
    data: List[Dict] = [monitor.__data__ for monitor in monitors]

    for mon in data:
        thumbnail = get_monitor_thumb(mon['identifier'])
        mon['thumbnail'] = thumbnail

    return jsonify(data)


def get_scopes(monitor_id: id, unit: str = "MONTH", page_number: int = 1, page_size: int = 15):
    request_filter = (MonitoringScope.monitor == monitor_id,) if unit is None or not unit.strip() else (
        MonitoringScope.monitor == monitor_id, MonitoringScope.unit == unit)

    scopes_count = MonitoringScope.select().where(*request_filter).count()

    scopes = (MonitoringScope
              .select()
              .where(*request_filter)
              .order_by(MonitoringScope.ends_at.desc())
              .paginate(page_number, page_size)
              )

    return scopes, scopes_count


@app.route("/api/v1/monitors/<monitor_name>/scopes")
def get_monitor_scopes(monitor_name):
    monitor = Monitor.get(Monitor.name == monitor_name)
    scopes, _ = get_scopes(monitor.id, page_size=50)
    data = [scope.__data__ for scope in scopes]
    return jsonify(data)


def get_video_url(file_name: str, expires_in: int = 60 * 5):
    return s3_client.meta.client.generate_presigned_url(
        'get_object',
        Params={'Bucket': "monitoring-storage", 'Key': file_name},
        ExpiresIn=expires_in,
    )


@app.route("/api/v1/monitors/<monitor_name>/scope/<scope_value>/output")
def get_scope_video_url(monitor_name, scope_value):
    monitor = Monitor.get(Monitor.name == monitor_name)
    scope = MonitoringScope.get(MonitoringScope.value == scope_value, MonitoringScope.monitor == monitor.id)
    expires_int = 60 * 5
    video_url = get_video_url(scope.output, expires_int)

    data = {
        "video_url": video_url,
        "expires_in": expires_int,
    }
    return jsonify(data)


@app.route("/")
@cache.cached(timeout=60 * 60 * 2)
def home():
    monitors = Monitor.select()
    return render_template('index.html', monitors=monitors)


def get_monitor_cache_key():
    unit = request.args.get('unit')
    return request.path if unit is None else request.path + "/" + unit


@app.route("/monitor/<monitor_name>/<int:page_number>")
@cache.cached(timeout=60 * 2, key_prefix=get_monitor_cache_key)
def monitor(monitor_name, page_number=1):
    monitor = Monitor.get(Monitor.name == monitor_name)
    monitor_id = monitor.id
    page_size = 15
    unit = request.args.get('unit')

    scopes, scopes_count = get_scopes(monitor_id, unit, page_number, page_size)

    num_pages = int(scopes_count / page_size)

    monitor_scopes_status = (MonitoringScope
                             .select(MonitoringScope.status, fn.COUNT(MonitoringScope.id).alias('scopes_count'))
                             .where(MonitoringScope.monitor == monitor_id)
                             .group_by(MonitoringScope.status))

    files_count = (MonitoringScope
                   .select(fn.SUM(MonitoringScope.files_count).alias('files_count'))
                   .where(MonitoringScope.monitor == monitor_id, MonitoringScope.unit == "DAY",
                          MonitoringScope.status == "ARCHIVED")
                   .scalar())

    return render_template(
        'monitor.html',
        monitor=monitor,
        scopes=scopes,
        scopes_count=scopes_count,
        num_pages=num_pages,
        page_number=page_number,
        statuses=monitor_scopes_status,
        files_count=files_count,
        unit=unit
    )


@app.route("/monitor/<monitor_name>/scope/<scope_value>")
@cache.cached(timeout=60 * 2)
def scope_watch(monitor_name, scope_value):
    monitor = Monitor.get(Monitor.name == monitor_name)
    scope = MonitoringScope.get(MonitoringScope.value == scope_value, MonitoringScope.monitor == monitor.id)
    video_url = get_video_url(scope.output)

    return render_template('scope.html', video_url=video_url, scope=scope)


if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5000)
