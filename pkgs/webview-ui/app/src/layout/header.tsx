import { createQuery } from "@tanstack/solid-query";
import { activeURI } from "../App";
import { callApi } from "../api";
import { Accessor, Show } from "solid-js";
import { useNavigate } from "@solidjs/router";

import Icon from "../components/icon";
import { Button } from "../components/button";

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
        <span class="tooltip tooltip-bottom lg:hidden" data-tip="Menu">
          <label
            class="btn btn-square btn-ghost drawer-button"
            for="toplevel-drawer"
          >
            <span class="material-icons">menu</span>
          </label>
        </span>
      </div>
      <div class="flex-1"></div>
      <div class="flex-none">
        <Show when={activeURI()}>
          {(d) => (
            <span class="tooltip tooltip-bottom" data-tip="Clan Settings">
              <Button
                variant="light"
                onClick={() => navigate(`/clans/${window.btoa(d())}`)}
                startIcon={<Icon icon="Settings" />}
              ></Button>
            </span>
          )}
        </Show>
      </div>
    </div>
  );
};
