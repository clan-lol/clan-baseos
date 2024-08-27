import { callApi, SuccessData } from "@/src/api";
import { BackButton } from "@/src/components/BackButton";
import { useParams } from "@solidjs/router";
import { createQuery } from "@tanstack/solid-query";
import { createEffect, For, Match, Switch } from "solid-js";
import { Show } from "solid-js";
import { DiskView } from "../disk/view";
import { Accessor } from "solid-js";

type AdminData = SuccessData<"get_admin_service">["data"];

interface ClanDetailsProps {
  admin: AdminData;
}

const ClanDetails = (props: ClanDetailsProps) => {
  const items = () =>
    Object.entries<string>(
      (props.admin?.config?.allowedKeys as Record<string, string>) || {},
    );

  return (
    <div>
      <h1>Clan Details </h1>
      <For each={items()}>
        {([name, key]) => (
          <div>
            <span>{name}</span>
            <span>{key}</span>
          </div>
        )}
      </For>
    </div>
  );
};

export const Details = () => {
  const params = useParams();
  const clan_dir = window.atob(params.id);
  const query = createQuery(() => ({
    queryKey: [clan_dir, "get_admin_service"],
    queryFn: async () => {
      const result = await callApi("get_admin_service", {
        base_url: clan_dir,
      });
      if (result.status === "error") throw new Error("Failed to fetch data");
      return result.data || null;
    },
  }));

  return (
    <div class="p-2">
      <BackButton />
      <Show
        when={!query.isLoading}
        fallback={<span class="loading loading-lg"></span>}
      >
        <Switch>
          <Match when={query.data}>
            {(d) => <ClanDetails admin={query.data} />}
          </Match>
        </Switch>
        {clan_dir}
      </Show>
    </div>
  );
};
