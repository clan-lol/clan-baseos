import { createQuery } from "@tanstack/solid-query";
import { activeURI } from "../App";
import { callApi } from "../api";
import { Accessor, Show } from "solid-js";
import { useNavigate } from "@solidjs/router";

import ArrowBottom from "@/icons/arrow-bottom.svg";

interface HeaderProps {
  clan_dir: Accessor<string | null>;
}
export const Header = (props: HeaderProps) => {
  const { clan_dir } = props;
  const navigate = useNavigate();

  const query = createQuery(() => ({
    queryKey: [clan_dir(), "meta"],
    queryFn: async () => {
      const curr = clan_dir();
      if (curr) {
        const result = await callApi("show_clan_meta", { uri: curr });
        if (result.status === "error") throw new Error("Failed to fetch data");
        return result.data;
      }
    },
  }));

  return (
    <div class="navbar">
      <div class="flex-none">
        <span class="tooltip tooltip-bottom" data-tip="Menu">
          <label
            class="btn btn-square btn-ghost drawer-button"
            for="toplevel-drawer"
          >
            <span class="material-icons">menu</span>
          </label>
        </span>
      </div>
      <div class="flex-1">
        <Show when={query.isLoading && !query.data}>
          <div class="skeleton mx-4 size-11 rounded-full"></div>
          <span class="flex flex-col gap-2">
            <div class="skeleton h-3 w-32"></div>
            <div class="skeleton h-3 w-40"></div>
          </span>
        </Show>
        <Show when={query.data}>
          {(meta) => (
            <div class="tooltip tooltip-right" data-tip={activeURI()}>
              <div class="avatar placeholder online mx-4">
                <div class="w-10 rounded-full bg-slate-700 text-3xl text-neutral-content">
                  <ArrowBottom />
                </div>
              </div>
            </div>
          )}
        </Show>
        <span class="flex flex-col">
          <Show when={query.data}>
            {(meta) => [
              <span class="text-primary-800">{meta().name}</span>,
              <span class="text-neutral">{meta()?.description}</span>,
            ]}
          </Show>
        </span>
      </div>
      <div class="flex-none">
        <Show when={activeURI()}>
          {(d) => (
            <span class="tooltip tooltip-bottom" data-tip="Clan Settings">
              <button
                class="link"
                onClick={() => navigate(`/clans/${window.btoa(d())}`)}
              >
                <span class="material-icons">settings</span>
              </button>
            </span>
          )}
        </Show>
      </div>
    </div>
  );
};
