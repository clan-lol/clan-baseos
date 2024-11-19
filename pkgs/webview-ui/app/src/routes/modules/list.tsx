import { callApi, SuccessData } from "@/src/api";
import { activeURI } from "@/src/App";
import { createModulesQuery } from "@/src/queries";
import { A, useNavigate } from "@solidjs/router";
import { createQuery, useQueryClient } from "@tanstack/solid-query";
import { createEffect, For, Match, Switch } from "solid-js";
import { SolidMarkdown } from "solid-markdown";

export type ModuleInfo = SuccessData<"list_modules">[string];

const ModuleListItem = (props: { name: string; info: ModuleInfo }) => {
  const { name, info } = props;
  const navigate = useNavigate();

  return (
    <div class="stat">
      <div class="stat-figure text-primary">
        <div class="join">more</div>
      </div>

      <A href={`/modules/${name}`}>
        <div class="stat-value underline">{name}</div>
      </A>

      <div>{info.description}</div>
    </div>
  );
};

export const ModuleList = () => {
  const modulesQuery = createModulesQuery(activeURI(), {
    features: ["inventory"],
  });
  return (
    <Switch fallback="Shit">
      <Match when={modulesQuery.isLoading}>Loading....</Match>
      <Match when={modulesQuery.data}>
        <div>
          Show Modules
          <For each={modulesQuery.data}>
            {([k, v]) => <ModuleListItem info={v} name={k} />}
          </For>
        </div>
      </Match>
    </Switch>
  );
};
