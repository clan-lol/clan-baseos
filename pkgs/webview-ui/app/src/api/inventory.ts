import { callApi, ClanService, ServiceNames, Services } from ".";
import { Schema as Inventory } from "@/api/Inventory";

export async function get_inventory(base_path: string) {
  const r = await callApi("get_inventory", {
    base_path,
  });
  if (r.status == "error") {
    throw new Error("Failed to get inventory");
  }
  const inventory: Inventory = r.data;
  return inventory;
}

export const single_instance_name = <T extends keyof Services>(
  machine_name: string,
  service_name: T,
) => `${machine_name}_${service_name}_0` as const;

function get_service<T extends ServiceNames>(base_path: string, service: T) {
  return callApi("get_inventory", { base_path }).then((r) => {
    if (r.status == "error") {
      return null;
    }
    const inventory: Inventory = r.data;

    const serviceInstance = inventory.services?.[service];
    return serviceInstance;
  });
}

export async function get_single_service<T extends keyof Services>(
  base_path: string,
  machine_name: string,
  service_name: T,
) {
  const instance_key = single_instance_name(machine_name, service_name);
  const service = await get_service(base_path, "admin");
  return service?.[instance_key];
}
