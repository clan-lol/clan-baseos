import { callApi } from "@/src/api";
import { Component, For, Show } from "solid-js";

import { createQuery } from "@tanstack/solid-query";
import { Button } from "@/src/components/button";
import Icon from "@/src/components/icon";

export const BlockDevicesView: Component = () => {
  const {
    data: devices,
    refetch: loadDevices,
    isFetching,
  } = createQuery(() => ({
    queryKey: ["block_devices"],
    queryFn: async () => {
      const result = await callApi("show_block_devices", { options: {} });
      if (result.status === "error") throw new Error("Failed to fetch data");

      return result.data;
    },
    staleTime: 1000 * 60 * 5,
  }));

  return (
    <div>
      <div class="tooltip tooltip-bottom" data-tip="Refresh">
        <Button
          onClick={() => loadDevices()}
          startIcon={<Icon icon="Update" />}
        ></Button>
      </div>
      <div class="flex max-w-screen-lg flex-col gap-4">
        {isFetching ? (
          <span class="loading loading-bars"></span>
        ) : (
          <Show when={devices}>
            {(devices) => (
              <For each={devices().blockdevices}>
                {(device) => (
                  <div class="stats shadow">
                    <div class="stat w-28 py-8">
                      <div class="stat-title">Name</div>
                      <div class="stat-value">
                        {" "}
                        <span class="material-icons">storage</span>{" "}
                        {device.name}
                      </div>
                      <div class="stat-desc"></div>
                    </div>

                    <div class="stat w-28">
                      <div class="stat-title">Size</div>
                      <div class="stat-value">{device.size}</div>
                      <div class="stat-desc"></div>
                    </div>
                  </div>
                )}
              </For>
            )}
          </Show>
        )}
      </div>
    </div>
  );
};
