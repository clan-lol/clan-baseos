import { get_inventory } from "./inventory";

export const instance_name = (machine_name: string) =>
  `${machine_name}-single-disk` as const;

export async function set_single_disk_id(
  base_path: string,
  machine_name: string,
  disk_id: string,
) {
  const inventory = await get_inventory(base_path);
  if (!inventory.services) {
    return new Error("No services found in inventory");
  }
  if (!inventory.services["single-disk"]) {
    inventory.services["single-disk"] = {};
  }
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
