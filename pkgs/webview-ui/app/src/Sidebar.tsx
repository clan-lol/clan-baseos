import { For, Show } from "solid-js";
import { activeURI } from "./App";
import { createQuery } from "@tanstack/solid-query";
import { callApi } from "./api";
import { A, RouteSectionProps } from "@solidjs/router";
import { AppRoute, routes } from "./index";

export const Sidebar = (props: RouteSectionProps) => {
  const clanQuery = createQuery(() => ({
    queryKey: [activeURI(), "meta"],
    queryFn: async () => {
      const curr = activeURI();
      if (curr) {
        const result = await callApi("show_clan_meta", { uri: curr });
        if (result.status === "error") throw new Error("Failed to fetch data");
        return result.data;
      }
    },
  }));

  return (
    <aside class="w-80 rounded-xl border border-slate-900 bg-slate-800 pb-10">
      <div class="m-4 flex flex-col text-center capitalize text-white">
        <span class="text-lg">{clanQuery.data?.name}</span>
        <span class="text-sm">{clanQuery.data?.description}</span>
        <RouteMenu class="menu px-4 py-2" routes={routes} />
      </div>
    </aside>
  );
};

const RouteMenu = (props: {
  class?: string;
  routes: AppRoute[];
  prefix?: string;
}) => (
  <ul class={props?.class}>
    <For each={props.routes.filter((r) => !r.hidden)}>
      {(route) => (
        <li>
          <Show
            when={route.children}
            fallback={
              <A href={[props.prefix, route.path].filter(Boolean).join("")}>
                <button class="text-white">
                  {route.icon && (
                    <span class="material-icons">{route.icon}</span>
                  )}
                  {route.label}
                </button>
              </A>
            }
          >
            {(children) => (
              <details id={`disclosure-${route.label}`} open={true}>
                <summary class="group">
                  {route.icon && (
                    <span class="material-icons">{route.icon}</span>
                  )}
                  {route.label}
                </summary>
                <RouteMenu
                  routes={children()}
                  prefix={[props.prefix, route.path].filter(Boolean).join("")}
                />
              </details>
            )}
          </Show>
        </li>
      )}
    </For>
  </ul>
);
