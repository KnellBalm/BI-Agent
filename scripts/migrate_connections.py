import json
import os
import shutil

def migrate_connections(config_path):
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found.")
        return

    # Backup
    backup_path = config_path + ".backup"
    shutil.copy2(config_path, backup_path)
    print(f"Backup created at {backup_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    migrated_data = {}
    for name, info in data.items():
        conn_type = info.get('type')
        config = info.get('config', {})
        
        new_config = {}
        if conn_type == 'postgres':
            new_config = {
                "host": config.get("POSTGRES_HOST", "localhost"),
                "port": config.get("POSTGRES_PORT", "5432"),
                "dbname": config.get("POSTGRES_DB", ""),
                "user": config.get("POSTGRES_USER", ""),
                "password": config.get("POSTGRES_PASSWORD", "")
            }
        elif conn_type == 'mysql':
            new_config = {
                "host": config.get("MYSQL_HOST", "localhost"),
                "port": config.get("MYSQL_PORT", "3306"),
                "dbname": config.get("MYSQL_DB", ""),
                "user": config.get("MYSQL_USER", ""),
                "password": config.get("MYSQL_PASSWORD", "")
            }
        else:
            new_config = config # Keep as is for other types

        migrated_data[name] = {
            "type": conn_type,
            "config": new_config
        }

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(migrated_data, f, indent=4)
    print(f"Successfully migrated {config_path} to V2 schema.")

if __name__ == "__main__":
    migrate_connections("backend/data/connections.json")
