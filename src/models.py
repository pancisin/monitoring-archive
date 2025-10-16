import os

from peewee import *

db = PostgresqlDatabase(
    database="storage_operator",
    user=os.environ["DB_USERNAME"],
    password=os.environ["DB_PASSWORD"],
    host=os.environ["DB_HOST"],
    port=os.environ["DB_PORT"],
)

db.connect()


class BaseModel(Model):
    class Meta:
        database = db


class Monitor(BaseModel):
    name = CharField(unique=True)
    path = CharField(unique=True)
    last_scan_at = DateTimeField(null=True)
    width = IntegerField(null=True)
    height = IntegerField(null=True)

    # def __init__(self, name: str, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.name = name


class MonitoringScope(BaseModel):
    unit = CharField(choices=["DAY", "WEEK", "MONTH"])
    value = CharField()
    starts_at = DateTimeField()
    ends_at = DateTimeField()
    path = CharField()
    files_count = IntegerField()
    monitor = ForeignKeyField(Monitor, backref="scopes")
    status = CharField(choices=["INCOMPLETE", "PENDING", "VOID", "PROCESSED", "ARCHIVED", "ERROR"],
                       default="INCOMPLETE")
    output = CharField(null=True)


db.create_tables([Monitor, MonitoringScope])
