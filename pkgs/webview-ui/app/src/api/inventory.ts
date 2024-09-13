import { QueryClient } from "@tanstack/solid-query";
import { callApi, ClanServiceInstance, ServiceNames, Services } from ".";

export async function get_inventory(client: QueryClient, base_path: string) {
  const data = await client.ensureQueryData({
    queryKey: [base_path, "inventory"],
    queryFn: () => {
      console.log("Refreshing inventory");
      return callApi("get_inventory", { base_path });
    },
    revalidateIfStale: true,
    staleTime: 60 * 1000,
  });

  return data;
}

export const generate_instance_name = <T extends keyof Services>(
  machine_name: string,
  service_name: T,
) => [machine_name, service_name, 1].filter(Boolean).join("_");

export const get_first_instance_name = async <T extends keyof Services>(
  client: QueryClient,
  base_path: string,
  service_name: T,
): Promise<string | null> => {
  const r = await get_inventory(client, base_path);
  if (r.status === "success") {
    const service = r.data.services?.[service_name];
    if (!service) return null;
    return Object.keys(service)[0] || null;
  }
  return null;
};

async function get_service<T extends ServiceNames>(
  client: QueryClient,
  base_path: string,
  service_name: T,
) {
  const r = await get_inventory(client, base_path);
  if (r.status === "success") {
    const service = r.data.services?.[service_name];
    return service as Services[T];
  }
  return null;
}

export async function get_single_service<T extends keyof Services>(
  client: QueryClient,
  base_path: string,
  service_name: T,
) {
  const instance_key = await get_first_instance_name(
    client,
    base_path,
    service_name,
  );

  if (!instance_key) {
    return {};
  }
  const service: Services[T] | null = await get_service(
    client,
    base_path,
    service_name,
  );
  if (service) {
    const clanServiceInstance = service[instance_key];
    return clanServiceInstance || {};
  }
  return {};
}

export async function set_single_service<T extends keyof Services>(
  client: QueryClient,
  base_path: string,
  machine_name: string,
  service_name: T,
  service_config: ClanServiceInstance<T>,
) {
  const instance_key =
    (await get_first_instance_name(client, base_path, service_name)) ||
    generate_instance_name(machine_name, service_name);
  const r = await get_inventory(client, base_path);
  if (r.status === "success") {
    const inventory = r.data;
    inventory.services = inventory.services || {};
    inventory.services[service_name] = inventory.services[service_name] || {};
    // @ts-expect-error: This doesn't check
    inventory.services[service_name][instance_key] = service_config;
    console.log("saving inventory", inventory);
    return callApi("set_inventory", {
      inventory,
      message: `update_single_service ${service_name}`,
      flake_dir: base_path,
    });
  }
  return r;
}
