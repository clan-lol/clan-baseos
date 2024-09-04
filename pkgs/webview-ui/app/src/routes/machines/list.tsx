import { type Component, For, Match, Switch } from "solid-js";
import { activeURI } from "@/src/App";
import { callApi, OperationResponse } from "@/src/api";
import toast from "solid-toast";
import { MachineListItem } from "@/src/components/MachineListItem";
import {
  createQueries,
  createQuery,
  useQueryClient,
} from "@tanstack/solid-query";
import { useNavigate } from "@solidjs/router";

type MachinesModel = Extract<
  OperationResponse<"list_inventory_machines">,
  { status: "success" }
>["data"];

type ExtendedMachine = MachinesModel & {
  nixOnly: boolean;
};

export const MachineListView: Component = () => {
  const queryClient = useQueryClient();

  const inventoryQuery = createQuery<MachinesModel>(() => ({
    queryKey: [activeURI(), "list_machines", "inventory"],
    placeholderData: {},
    enabled: !!activeURI(),
    queryFn: async () => {
      const uri = activeURI();
      if (uri) {
        const response = await callApi("list_inventory_machines", {
          flake_url: uri,
        });
        if (response.status === "error") {
          toast.error("Failed to fetch data");
        } else {
          return response.data;
        }
      }
      return {};
    },
  }));

  const nixosQuery = createQuery<string[]>(() => ({
    queryKey: [activeURI(), "list_machines", "nixos"],
    enabled: !!activeURI(),
    placeholderData: [],
    queryFn: async () => {
      const uri = activeURI();
      if (uri) {
        const response = await callApi("list_nixos_machines", {
          flake_url: uri,
        });
        if (response.status === "error") {
          toast.error("Failed to fetch data");
        } else {
          return response.data;
        }
      }
      return [];
    },
  }));

  const refresh = async () => {
    queryClient.invalidateQueries({
      // Invalidates the cache for of all types of machine list at once
      queryKey: [activeURI(), "list_machines"],
    });
  };

  const inventoryMachines = () => Object.entries(inventoryQuery.data || {});
  const nixOnlyMachines = () =>
    nixosQuery.data?.filter(
      (name) => !inventoryMachines().some(([key, machine]) => key === name),
    );
  const navigate = useNavigate();

  return (
    <div>
      <div class="tooltip tooltip-bottom" data-tip="Open Clan"></div>
      <div class="tooltip tooltip-bottom" data-tip="Refresh">
        <button class="btn btn-ghost" onClick={() => refresh()}>
          <span class="material-icons ">refresh</span>
        </button>
      </div>
      <div class="tooltip tooltip-bottom" data-tip="Create machine">
        <button class="btn btn-ghost" onClick={() => navigate("create")}>
          <span class="material-icons ">add</span>
        </button>
      </div>
      <Switch>
        <Match when={inventoryQuery.isLoading}>
          {/* Loading skeleton */}
          <div>
            <div class="card card-side m-2 bg-base-100 shadow-lg">
              <figure class="pl-2">
                <div class="skeleton size-12"></div>
              </figure>
              <div class="card-body">
                <h2 class="card-title">
                  <div class="skeleton h-12 w-80"></div>
                </h2>
                <div class="skeleton h-8 w-72"></div>
              </div>
            </div>
          </div>
        </Match>
        <Match
          when={
            !inventoryQuery.isLoading &&
            inventoryMachines().length === 0 &&
            nixOnlyMachines()?.length === 0
          }
        >
          <div class="mt-8 flex w-full flex-col items-center justify-center gap-2">
            <span class="text-lg text-neutral">
              No machines defined yet. Click below to define one.
            </span>
            <button
              class="btn btn-square btn-ghost size-28 overflow-hidden p-2"
              onClick={() => navigate("/machines/create")}
            >
              <span class="material-icons text-6xl font-light">add</span>
            </button>
          </div>
        </Match>
        <Match when={!inventoryQuery.isLoading}>
          <ul>
            <For each={inventoryMachines()}>
              {([name, info]) => <MachineListItem name={name} info={info} />}
            </For>
            <For each={nixOnlyMachines()}>
              {(name) => <MachineListItem name={name} nixOnly={true} />}
            </For>
          </ul>
        </Match>
      </Switch>
    </div>
  );
};
