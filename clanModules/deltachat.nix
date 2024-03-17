{ config, pkgs, ... }:
{
  networking.firewall.interfaces."zt+".allowedTCPPorts = [ 25 ]; # smtp with other hosts
  environment.systemPackages = [ pkgs.deltachat-desktop ];

  services.maddy =
    let
      domain = "${config.clanCore.machineName}.local";
    in
    {
      enable = true;
      primaryDomain = domain;
      config = ''
        # Minimal configuration with TLS disabled, adapted from upstream example
        # configuration here https://github.com/foxcpp/maddy/blob/master/maddy.conf
        # Do not use this in unencrypted networks!

        auth.pass_table local_authdb {
          table sql_table {
            driver sqlite3
            dsn credentials.db
            table_name passwords
          }
        }

        storage.imapsql local_mailboxes {
          driver sqlite3
          dsn imapsql.db
        }

        table.chain local_rewrites {
          optional_step regexp "(.+)\+(.+)@(.+)" "$1@$3"
          optional_step static {
            entry postmaster postmaster@$(primary_domain)
          }
          optional_step file /etc/maddy/aliases
        }

        msgpipeline local_routing {
          destination postmaster $(local_domains) {
            modify {
              replace_rcpt &local_rewrites
            }
            deliver_to &local_mailboxes
          }
          default_destination {
            reject 550 5.1.1 "User doesn't exist"
          }
        }

        smtp tcp://[::]:25 {
          limits {
            all rate 20 1s
            all concurrency 10
          }
          dmarc yes
          check {
            require_mx_record
            dkim
            spf
          }
          source $(local_domains) {
            reject 501 5.1.8 "Use Submission for outgoing SMTP"
          }
          default_source {
            destination postmaster $(local_domains) {
              deliver_to &local_routing
            }
            default_destination {
              reject 550 5.1.1 "User doesn't exist"
            }
          }
        }

        submission tcp://[::1]:587 {
          limits {
            all rate 50 1s
          }
          auth &local_authdb
          source $(local_domains) {
            check {
                authorize_sender {
                    prepare_email &local_rewrites
                    user_to_email identity
                }
            }
            destination postmaster $(local_domains) {
                deliver_to &local_routing
            }
            default_destination {
                modify {
                    dkim $(primary_domain) $(local_domains) default
                }
                deliver_to &remote_queue
            }
          }
          default_source {
            reject 501 5.1.8 "Non-local sender domain"
          }
        }

        target.remote outbound_delivery {
          limits {
            destination rate 20 1s
            destination concurrency 10
          }
          mx_auth {
            dane
            mtasts {
              cache fs
              fs_dir mtasts_cache/
            }
            local_policy {
                min_tls_level encrypted
                min_mx_level none
            }
          }
        }

        target.queue remote_queue {
          target &outbound_delivery
          autogenerated_msg_domain $(primary_domain)
          bounce {
            destination postmaster $(local_domains) {
              deliver_to &local_routing
            }
            default_destination {
                reject 550 5.0.0 "Refusing to send DSNs to non-local addresses"
            }
          }
        }

        imap tcp://[::1]:143 {
          auth &local_authdb
          storage &local_mailboxes
        }
      '';
      ensureAccounts = [ "user@${domain}" ];
      ensureCredentials = {
        "user@${domain}".passwordFile = pkgs.writeText "dummy" "foobar";
      };
    };
}
