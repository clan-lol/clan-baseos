import { QueryClient } from "@tanstack/query-core";
import { get_inventory } from "./inventory";

export const instance_name = (machine_name: string) =>
  `${machine_name}-single-disk` as const;

export async function set_single_disk_id(
  client: QueryClient,
  base_path: string,
  machine_name: string,
  disk_id: string,
) {
  const r = await get_inventory(client, base_path);
  if (r.status === "error") {
    return r;
  }
  if (!r.data.services) {
    return new Error("No services found in inventory");
  }
  const inventory = r.data;
  inventory.services = inventory.services || {};
  inventory.services["single-disk"] = inventory.services["single-disk"] || {};

  inventory.services["single-disk"][instance_name(machine_name)] = {
    meta: {
      name: instance_name(machine_name),
    },
    roles: {
      default: {
        machines: [machine_name],
        config: {
          device: `/dev/disk/by-id/${disk_id}`,
        },
      },
    },
  };
}
