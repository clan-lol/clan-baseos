import subprocess


class Error(Exception):
    pass


def is_valid_age_key(secret_key: str) -> bool:
    # Run the age-keygen command with the -y flag to check the key format
    result = subprocess.run(
        ["age-keygen", "-y"],
        input=secret_key,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        return True
    msg = f"Invalid age key: {secret_key}"
    raise Error(msg)
