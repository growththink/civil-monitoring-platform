#!/bin/sh
# Run inside mosquitto container once to create the password file:
#   docker compose exec mosquitto sh /mosquitto/config/setup_users.sh
# Or run from host:
#   docker compose run --rm mosquitto mosquitto_passwd -c -b /mosquitto/config/passwd ingest ingest_pw
mosquitto_passwd -c -b /mosquitto/config/passwd ingest ingest_pw
mosquitto_passwd -b /mosquitto/config/passwd device_demo device_demo_pw
echo "Users created. Restart mosquitto for changes to take effect."
