import os
import boto3

from botocore.config import Config
from flask import Flask, render_template
from flask_caching import Cache

from src.models import Monitor, MonitoringScope
from peewee import fn

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


@app.route("/")
@cache.cached(timeout=60 * 60 * 2)
def home():
    monitors = Monitor.select()
    return render_template('index.html', monitors=monitors)


@app.route("/monitor/<monitor_name>/<int:page_number>")
@cache.cached(timeout=60 * 2)
def monitor(monitor_name, page_number=1):
    monitor = Monitor.get(Monitor.name == monitor_name)
    monitor_id = monitor.id
    page_size = 15

    scopes_count = MonitoringScope.select().where(MonitoringScope.monitor == monitor_id).count()

    scopes = (MonitoringScope
              .select()
              .where(MonitoringScope.monitor == monitor_id)
              .order_by(MonitoringScope.ends_at.desc())
              .paginate(page_number, page_size)
              )

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
    )


@app.route("/monitor/<monitor_name>/scope/<scope_value>")
@cache.cached(timeout=60 * 2)
def scope_watch(monitor_name, scope_value):
    monitor = Monitor.get(Monitor.name == monitor_name)
    scope = MonitoringScope.get(MonitoringScope.value == scope_value, MonitoringScope.monitor == monitor.id)
    presigned_url = s3_client.meta.client.generate_presigned_url(
        'get_object',
        Params={'Bucket': "monitoring-storage", 'Key': scope.output},
        ExpiresIn=60 * 5,

    )

    return render_template('scope.html', video_url=presigned_url, scope=scope)


if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5000)
