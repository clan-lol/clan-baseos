import { callApi, SuccessData } from "@/src/api";
import { activeURI } from "@/src/App";
import { BackButton } from "@/src/components/BackButton";
import { createModulesQuery } from "@/src/queries";
import { useParams } from "@solidjs/router";
import { For, Match, Switch } from "solid-js";
import { SolidMarkdown } from "solid-markdown";
import toast from "solid-toast";
import { ModuleInfo } from "./list";

export const ModuleDetails = () => {
  const params = useParams();
  const modulesQuery = createModulesQuery(activeURI());

  return (
    <div class="p-1">
      <BackButton />
      <div class="p-2">
        <h3 class="text-2xl">{params.id}</h3>
        <Switch>
          <Match when={modulesQuery.data?.find((i) => i[0] === params.id)}>
            {(d) => <Details data={d()[1]} id={d()[0]} />}
          </Match>
        </Switch>
      </div>
    </div>
  );
};

function deepMerge(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  obj1: Record<string, any>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  obj2: Record<string, any>,
) {
  const result = { ...obj1 };

  for (const key in obj2) {
    if (Object.prototype.hasOwnProperty.call(obj2, key)) {
      if (obj2[key] instanceof Object && obj1[key] instanceof Object) {
        result[key] = deepMerge(obj1[key], obj2[key]);
      } else {
        result[key] = obj2[key];
      }
    }
  }

  return result;
}

interface DetailsProps {
  data: ModuleInfo;
  id: string;
}
const Details = (props: DetailsProps) => {
  return (
    <div class="flex w-full flex-col gap-2">
      <article class="prose">{props.data.description}</article>
      <span class="label-text">Categories</span>
      <div>
        <For each={props.data.categories}>
          {(c) => <div class="badge badge-primary m-1">{c}</div>}
        </For>
      </div>
      <span class="label-text">Roles</span>
      <div>
        <For each={props.data.roles}>
          {(r) => <div class="badge badge-secondary m-1">{r}</div>}
        </For>
      </div>
      <div class="p-2">
        <SolidMarkdown>{props.data.readme}</SolidMarkdown>
      </div>
      <div class="my-2 flex w-full gap-2">
        <button
          class="btn btn-primary"
          onClick={async () => {
            const uri = activeURI();
            if (!uri) return;
            const res = await callApi("get_inventory", { base_path: uri });
            if (res.status === "error") {
              toast.error("Failed to fetch inventory");
              return;
            }
            const inventory = res.data;
            const newInventory = deepMerge(inventory, {
              services: {
                [props.id]: {
                  default: {
                    enabled: false,
                  },
                },
              },
            });

            callApi("set_inventory", {
              flake_dir: uri,
              inventory: newInventory,
              message: `Add module: ${props.id} in 'default' instance`,
            });
          }}
        >
          <span class="material-icons ">add</span>
          Add to Clan
        </button>
      </div>
    </div>
  );
};
