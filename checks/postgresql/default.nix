(import ../lib/container-test.nix) ({
  name = "postgresql";

  nodes.machine =
    { self, config, ... }:
    {
      imports = [
        self.nixosModules.clanCore
        self.clanModules.postgresql
        self.clanModules.localbackup
      ];
      clan.postgresql.users.test = { };
      clan.postgresql.databases.test.create.options.OWNER = "test";
      clan.postgresql.databases.test.restore.stopOnRestore = [ "sample-service" ];
      clan.localbackup.targets.hdd.directory = "/mnt/external-disk";
      clan.core.clanDir = ./.;

      clan.core.machine = {
        id = "df97124f09da48e3a22d77ce30ee8da6";
        diskId = "c9c52c";
      };

      systemd.services.sample-service = {
        wantedBy = [ "multi-user.target" ];
        script = ''
          while true; do
            echo "Hello, world!"
            sleep 5
          done
        '';
      };

      environment.systemPackages = [ config.services.postgresql.package ];
    };
  testScript =
    { nodes, ... }:
    ''
      start_all()
      machine.wait_for_unit("postgresql")
      machine.wait_for_unit("sample-service")
      # Create a test table
      machine.succeed("runuser -u postgres -- /run/current-system/sw/bin/psql -c 'CREATE TABLE test (id serial PRIMARY KEY);' test")

      machine.succeed("/run/current-system/sw/bin/localbackup-create >&2")
      timestamp_before = int(machine.succeed("systemctl show --property=ExecMainStartTimestampMonotonic sample-service | cut -d= -f2").strip())

      machine.succeed("test -e /mnt/external-disk/snapshot.0/machine/var/backup/postgres/test/pg-dump || { echo 'pg-dump not found'; exit 1; }")
      machine.succeed("runuser -u postgres -- /run/current-system/sw/bin/psql -d test -c 'INSERT INTO test DEFAULT VALUES;'")
      machine.succeed("runuser -u postgres -- /run/current-system/sw/bin/psql -d test -c 'DROP TABLE test;'")
      machine.succeed("test -e /var/backup/postgres/test/pg-dump || { echo 'pg-dump not found'; exit 1; }")

      machine.succeed("rm -rf /var/backup/postgres")

      machine.succeed("NAME=/mnt/external-disk/snapshot.0 FOLDERS=/var/backup/postgres/test /run/current-system/sw/bin/localbackup-restore >&2")
      machine.succeed("test -e /var/backup/postgres/test/pg-dump || { echo 'pg-dump not found'; exit 1; }")

      machine.succeed("""
      set -x
      ${nodes.machine.clan.core.state.test.postRestoreCommand}
      """)
      machine.succeed("runuser -u postgres -- /run/current-system/sw/bin/psql -l >&2")
      machine.succeed("runuser -u postgres -- /run/current-system/sw/bin/psql -d test -c '\dt' >&2")

      timestamp_after = int(machine.succeed("systemctl show --property=ExecMainStartTimestampMonotonic sample-service | cut -d= -f2").strip())
      assert timestamp_before < timestamp_after, f"{timestamp_before} >= {timestamp_after}: expected sample-service to be restarted after restore"

      # Check that the table is still there
      machine.succeed("runuser -u postgres -- /run/current-system/sw/bin/psql -d test -c 'SELECT * FROM test;'")
      output = machine.succeed("runuser -u postgres -- /run/current-system/sw/bin/psql --csv -c \"SELECT datdba::regrole FROM pg_database WHERE datname = 'test'\"")
      owner = output.split("\n")[1]
      assert owner == "test", f"Expected database owner to be 'test', got '{owner}'"

      # check if restore works if the database does not exist
      machine.succeed("runuser -u postgres -- dropdb test")
      machine.succeed("${nodes.machine.clan.core.state.test.postRestoreCommand}")
      machine.succeed("runuser -u postgres -- /run/current-system/sw/bin/psql -d test -c '\dt' >&2")
    '';
})
