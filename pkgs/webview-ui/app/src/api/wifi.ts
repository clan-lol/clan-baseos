import { callApi } from ".";
import { Schema as Inventory } from "@/api/Inventory";

export const instance_name = (machine_name: string) =>
  `${machine_name}_wifi_0` as const;

export async function get_iwd_service(base_path: string, machine_name: string) {
  const r = await callApi("get_inventory", {
    base_path,
  });
  if (r.status == "error") {
    return null;
  }
  const inventory: Inventory = r.data;

  const instance_key = instance_name(machine_name);
  return inventory.services?.iwd?.[instance_key] || null;
}
