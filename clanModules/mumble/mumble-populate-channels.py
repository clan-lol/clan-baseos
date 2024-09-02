import argparse
import json
import os
import sqlite3


def ensure_config(path: str, db_path: str) -> None:
    # Default JSON structure if the file doesn't exist
    default_json = {
        "misc": {
            "audio_wizard_has_been_shown": True,
            "database_location": db_path,
            "viewed_server_ping_consent_message": True,
        },
        "settings_version": 1,
    }

    # Check if the file exists
    if os.path.exists(path):
        with open(path) as file:
            data = json.load(file)
    else:
        data = default_json
        # Create the file with default JSON structure
        with open(path, "w") as file:
            json.dump(data, file, indent=4)

    # TODO: make sure to only update the diff
    updated_data = {**default_json, **data}

    # Write the modified JSON object back to the file
    with open(path, "w") as file:
        json.dump(updated_data, file, indent=4)


def initialize_database(db_location: str) -> None:
    """
    Initializes the database. If the database or the servers table does not exist, it creates them.

    :param db_location: The path to the SQLite database
    """
    conn = sqlite3.connect(db_location)
    try:
        cursor = conn.cursor()

        # Create the servers table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            hostname TEXT NOT NULL,
            port INTEGER NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            url TEXT
        )
        """)

        # Commit the changes
        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred while initializing the database: {e}")
    finally:
        conn.close()


def initialize_certificates(
    db_location: str, hostname: str, port: str, digest: str
) -> None:
    # Connect to the SQLite database
    conn = sqlite3.connect(db_location)

    try:
        # Create a cursor object
        cursor = conn.cursor()

        # TODO: check if cert already there
        # if server_check(cursor, name, hostname):
        #     print(
        #         f"Server with name '{name}' and hostname '{hostname}' already exists."
        #     )
        #     return

        # SQL command to insert data into the servers table
        insert_query = """
        INSERT INTO cert (hostname, port, digest)
        VALUES (?, ?, ?)
        """

        # Data to be inserted
        data = (hostname, port, digest)

        # Execute the insert command with the provided data
        cursor.execute(insert_query, data)

        # Commit the changes
        conn.commit()

        print("Data has been successfully inserted.")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the connection
        conn.close()


def calculate_digest(cert: str) -> str:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes

    cert = cert.strip()
    cert = cert.encode("utf-8")
    cert = x509.load_pem_x509_certificate(cert, default_backend())
    digest = cert.fingerprint(hashes.SHA1()).hex()
    return digest


def server_check(cursor: str, name: str, hostname: str) -> bool:
    """
    Check if a server with the given name and hostname already exists.

    :param cursor: The database cursor
    :param name: The name of the server
    :param hostname: The hostname of the server
    :return: True if the server exists, False otherwise
    """
    check_query = """
    SELECT 1 FROM servers WHERE name = ? AND hostname = ?
    """
    cursor.execute(check_query, (name, hostname))
    return cursor.fetchone() is not None


def insert_server(
    name: str,
    hostname: str,
    port: str,
    username: str,
    password: str,
    url: str,
    db_location: str,
) -> None:
    """
    Inserts a new server record into the servers table.

    :param name: The name of the server
    :param hostname: The hostname of the server
    :param port: The port number
    :param username: The username
    :param password: The password
    :param url: The URL
    """
    # Connect to the SQLite database
    conn = sqlite3.connect(db_location)

    try:
        # Create a cursor object
        cursor = conn.cursor()

        if server_check(cursor, name, hostname):
            print(
                f"Server with name '{name}' and hostname '{hostname}' already exists."
            )
            return

        # SQL command to insert data into the servers table
        insert_query = """
        INSERT INTO servers (name, hostname, port, username, password, url)
        VALUES (?, ?, ?, ?, ?, ?)
        """

        # Data to be inserted
        data = (name, hostname, port, username, password, url)

        # Execute the insert command with the provided data
        cursor.execute(insert_query, data)

        # Commit the changes
        conn.commit()

        print("Data has been successfully inserted.")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the connection
        conn.close()


if __name__ == "__main__":
    port = 64738
    password = ""
    url = None

    parser = argparse.ArgumentParser(
        prog="initialize_mumble",
    )

    subparser = parser.add_subparsers(dest="certificates")
    # cert_parser = subparser.add_parser("certificates")

    parser.add_argument("--cert")
    parser.add_argument("--digest")
    parser.add_argument("--machines")
    parser.add_argument("--servers")
    parser.add_argument("--username")
    parser.add_argument("--db-location")
    parser.add_argument("--ensure-config")
    args = parser.parse_args()

    print(args)

    if args.ensure_config:
        ensure_config(args.ensure_config, args.db_location)
        print("Initialized config")
        exit(0)

    if args.servers:
        print(args.servers)
        servers = json.loads(f"{args.servers}")
        db_location = args.db_location
        for server in servers:
            digest = calculate_digest(server.get("value"))
            name = server.get("name")
            initialize_certificates(db_location, name, port, digest)
        print("Initialized certificates")
        exit(0)

    initialize_database(args.db_location)

    # Insert the server into the database
    print(args.machines)
    machines = json.loads(f"{args.machines}")
    print(machines)
    print(list(machines))

    for machine in list(machines):
        print(f"Inserting {machine}.")
        insert_server(
            machine,
            machine,
            port,
            args.username,
            password,
            url,
            args.db_location,
        )
