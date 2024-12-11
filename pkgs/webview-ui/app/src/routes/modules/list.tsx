import { SuccessData } from "@/src/api";
import { activeURI } from "@/src/App";
import { Button } from "@/src/components/button";
import { Header } from "@/src/layout/header";
import { createModulesQuery } from "@/src/queries";
import { A, useNavigate } from "@solidjs/router";
import { createSignal, For, Match, Switch } from "solid-js";
import { Typography } from "@/src/components/Typography";
import { Menu } from "@/src/components/Menu";
import { makePersisted } from "@solid-primitives/storage";
import { useQueryClient } from "@tanstack/solid-query";
import cx from "classnames";
import Icon from "@/src/components/icon";

export type ModuleInfo = SuccessData<"list_modules">[string];

interface CategoryProps {
  categories: string[];
}
const Categories = (props: CategoryProps) => {
  return (
    <span class="ml-6 inline-flex h-full align-middle">
      {props.categories.map((category) => (
        <span class="badge badge-secondary">{category}</span>
      ))}
    </span>
  );
};

interface RolesProps {
  roles: string[];
}
const Roles = (props: RolesProps) => {
  return (
    <div>
      <span>
        <Typography hierarchy="body" size="xs">
          Service Typography{" "}
        </Typography>
      </span>
      {props.roles.map((role) => (
        <span class="badge badge-ghost">{role}</span>
      ))}
    </div>
  );
};

const ModuleItem = (props: {
  name: string;
  info: ModuleInfo;
  class?: string;
}) => {
  const { name, info } = props;
  const navigate = useNavigate();

  return (
    <div class={cx("stat rounded-lg shadow-md", props.class)}>
      <div class="stat-figure text-primary-800">
        <div class="join">
          <Menu popoverid={`menu-${props.name}`} label={<Icon icon={"More"} />}>
            <ul class="menu z-[1] w-52 rounded-box bg-base-100 p-2 shadow">
              <li>
                <a
                  onClick={() => {
                    navigate(`/modules/details/${name}`);
                  }}
                >
                  Configure
                </a>
              </li>
            </ul>
          </Menu>
        </div>
      </div>

      <A href={`/modules/details/${name}`}>
        <div class="stat-value underline">
          {name}
          <Categories categories={info.categories} />
        </div>
      </A>

      <div class="w-full">
        <Typography hierarchy="body" size="default">
          {info.description}
        </Typography>
      </div>
      <Roles roles={info.roles || []} />
    </div>
  );
};

export const ModuleList = () => {
  const queryClient = useQueryClient();
  const modulesQuery = createModulesQuery(activeURI(), {
    features: ["inventory"],
  });

  const [view, setView] = makePersisted(createSignal<"list" | "grid">("list"), {
    name: "modules_view",
    storage: localStorage,
  });

  const refresh = async () => {
    queryClient.invalidateQueries({
      // Invalidates the cache for of all types of machine list at once
      queryKey: [activeURI(), "list_modules"],
    });
  };
  return (
    <>
      <Header
        title="Modules"
        toolbar={
          <>
            <span class="tooltip tooltip-bottom" data-tip="Reload">
              <Button
                variant="light"
                size="s"
                onClick={() => refresh()}
                startIcon={<Icon icon="Update" />}
              ></Button>
            </span>

            <div class="border border-def-3">
              <span class="tooltip tooltip-bottom" data-tip="List View">
                <Button
                  onclick={() => setView("list")}
                  variant={view() == "list" ? "dark" : "light"}
                  size="s"
                  startIcon={<Icon icon="List" />}
                ></Button>
              </span>
              <span class="tooltip tooltip-bottom" data-tip="Grid View">
                <Button
                  onclick={() => setView("grid")}
                  variant={view() == "grid" ? "dark" : "light"}
                  size="s"
                  startIcon={<Icon icon="Grid" />}
                ></Button>
              </span>
            </div>
            <span class="tooltip tooltip-bottom" data-tip="New Machine">
              <Button
                size="s"
                variant="light"
                startIcon={<Icon icon="CaretUp" />}
              >
                Import Module
              </Button>
            </span>
          </>
        }
      />
      <Switch fallback="Error">
        <Match when={modulesQuery.isFetching}>Loading....</Match>
        <Match when={modulesQuery.data}>
          <div
            class="my-4 flex flex-wrap gap-6 px-3 py-2"
            classList={{
              "flex-col": view() === "list",
              "": view() === "grid",
            }}
          >
            <For each={modulesQuery.data}>
              {([k, v]) => (
                <ModuleItem
                  info={v}
                  name={k}
                  class={view() == "grid" ? cx("max-w-md") : ""}
                />
              )}
            </For>
          </div>
        </Match>
      </Switch>
    </>
  );
};
