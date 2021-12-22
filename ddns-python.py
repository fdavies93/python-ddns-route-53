import boto3
import requests
from datetime import datetime, time, timedelta, timezone
import re
import sys
import itertools

def make_upsert_obj(record, new_ip : str):
    return {
        "Action": "UPSERT",
        "ResourceRecordSet": {
            "ResourceRecords": [ { "Value": new_ip } ],
            "Name": record["Name"],
            "Type": record["Type"],
            "TTL": record["TTL"]
        }
    }

hosted_zone = "HOSTED_ZONE_KEY"
name_patterns = ["path.*\.example\.site\."]
types = ["A"]
ttl = 60
log_path = "./ddns.log"

external_ip = requests.get("http://checkip.amazonaws.com/").text.replace("\n","")

tz = timezone(timedelta(hours=8))

time_now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")

print("Updating Route 53 DDNS at system time " + time_now)
print("Current IP is " + external_ip)

# validate external IP
ip_pattern : str = str('^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}')

if not re.match(ip_pattern, external_ip):
    print ("Malformed IP address, exiting.")
    sys.exit(1)

# get aws records
client = boto3.client("route53")

records = client.list_resource_record_sets(HostedZoneId=hosted_zone)

match_records = []

for record in records['ResourceRecordSets']:
    if record['Type'] in types:
        for pattern in name_patterns:
            if re.match(pattern, record['Name']):
                match_records.append(record)
                break
# print (records)
to_update = list(filter(lambda record: record['ResourceRecords'][0]['Value'] != external_ip, match_records))

if len(to_update) == 0:
    print ("Nothing to update, exiting.")
    sys.exit(0)

bulk_update = { "Comment": "Updating IPs to match dev server.", "Changes": [] }
write_out = []

with open(log_path,'a',encoding="utf-8") as log:
    for r in to_update:
        write_out.append("\n[" + time_now + "] " + "Update " + r["Name"] + " to " + external_ip)
        print (write_out[-1])
        bulk_update["Changes"].append(make_upsert_obj(r, external_ip))
    log.writelines(write_out)

client.change_resource_record_sets(HostedZoneId=hosted_zone,ChangeBatch=bulk_update)

sys.exit(0)