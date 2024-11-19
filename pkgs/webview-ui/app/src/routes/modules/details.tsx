import { callApi } from "@/src/api";
import { activeURI } from "@/src/App";
import { BackButton } from "@/src/components/BackButton";
import { createModulesQuery } from "@/src/queries";
import { useParams, useNavigate } from "@solidjs/router";
import {
  createEffect,
  createSignal,
  For,
  JSX,
  Match,
  Show,
  Switch,
} from "solid-js";
import { SolidMarkdown } from "solid-markdown";
import toast from "solid-toast";
import { ModuleInfo } from "./list";
import { createQuery } from "@tanstack/solid-query";
import { JSONSchema7 } from "json-schema";
import { TextInput } from "@/src/components/TextInput";
import {
  createForm,
  getValue,
  setValue,
  SubmitHandler,
} from "@modular-forms/solid";
import { DynForm } from "@/src/Form/form";

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
  const navigate = useNavigate();
  const add = async () => {
    navigate(`/modules/add/${props.id}`);
    // const uri = activeURI();
    // if (!uri) return;
    // const res = await callApi("get_inventory", { base_path: uri });
    // if (res.status === "error") {
    //   toast.error("Failed to fetch inventory");
    //   return;
    // }
    // const inventory = res.data;
    // const newInventory = deepMerge(inventory, {
    //   services: {
    //     [props.id]: {
    //       default: {
    //         enabled: false,
    //       },
    //     },
    //   },
    // });

    // callApi("set_inventory", {
    //   flake_dir: uri,
    //   inventory: newInventory,
    //   message: `Add module: ${props.id} in 'default' instance`,
    // });
  };
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
        <button class="btn btn-primary" onClick={add}>
          <span class="material-icons ">add</span>
          Add to Clan
        </button>
        {/* Add -> Select (required) roles, assign Machine */}
      </div>
      <ModuleForm id={props.id} />
    </div>
  );
};

type ModuleSchemasType = Record<string, Record<string, JSONSchema7>>;

const Unsupported = (props: { schema: JSONSchema7; what: string }) => (
  <div>
    Cannot render {props.what}
    <pre>
      <code>{JSON.stringify(props.schema, null, 2)}</code>
    </pre>
  </div>
);

function removeTrailingS(str: string) {
  // Check if the last character is "s" or "S"
  if (str.endsWith("s") || str.endsWith("S")) {
    return str.slice(0, -1); // Remove the last character
  }
  return str; // Return unchanged if no trailing "s"
}
interface SchemaFormProps {
  title: string;
  schema: JSONSchema7;
  path: string[];
}

export const ModuleForm = (props: { id: string }) => {
  // TODO: Fetch the synced schema for all the modules at runtime
  // We use static schema file at build time for now. (Different versions might have different schema at runtime)
  const schemaQuery = createQuery(() => ({
    queryKey: [activeURI(), "modules_schema"],
    queryFn: async () => {
      const moduleSchema = await import(
        "../../../api/modules_schemas.json"
      ).then((m) => m.default as ModuleSchemasType);

      return moduleSchema;
    },
  }));

  createEffect(() => {
    console.log("Schema Query", schemaQuery.data?.[props.id]);
  });

  const handleSubmit: SubmitHandler<NonNullable<unknown>> = async (
    values,
    event,
  ) => {
    console.log("Submitted form values", values);
  };

  return (
    <div id="ModuleForm">
      <Switch fallback={"No Schema found"}>
        <Match when={schemaQuery.isLoading}>Loading...</Match>
        <Match when={schemaQuery.data?.[props.id]}>
          {(rolesSchemas) => (
            <>
              Configure this module
              <For each={Object.entries(rolesSchemas())}>
                {([role, schema]) => (
                  <div class="my-2">
                    <h4 class="text-xl">{role}</h4>
                    <DynForm
                      handleSubmit={handleSubmit}
                      schema={schema}
                      components={{
                        after: <button class="btn btn-primary">Submit</button>,
                      }}
                    />
                  </div>
                )}
              </For>
            </>
          )}
        </Match>
      </Switch>
    </div>
  );
};
