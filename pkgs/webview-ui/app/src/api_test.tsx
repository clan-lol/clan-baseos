import {
  createForm,
  FieldValues,
  getValues,
  SubmitHandler,
} from "@modular-forms/solid";
import { TextInput } from "./components/TextInput";
import { Button } from "./components/button";
import { callApi } from "./api";
import { API } from "@/api/API";
import { createSignal, Match, Switch } from "solid-js";
import { Typography } from "./components/Typography";
import { createQuery } from "@tanstack/solid-query";
import { makePersisted } from "@solid-primitives/storage";

interface APITesterForm extends FieldValues {
  endpoint: string;
  payload: string;
}

export const ApiTester = () => {
  const [persistedTestData, setPersistedTestData] = makePersisted(
    createSignal<APITesterForm>(),
    {
      name: "_test_data",
      storage: localStorage,
    },
  );

  const [formStore, { Form, Field }] = createForm<APITesterForm>({
    initialValues: persistedTestData(),
  });

  const query = createQuery(() => ({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: [],
    queryFn: async () => {
      const values = getValues(formStore);
      return await callApi(
        values.endpoint as keyof API,
        JSON.parse(values.payload || ""),
      );
    },
    staleTime: Infinity,
  }));

  const handleSubmit: SubmitHandler<APITesterForm> = (values) => {
    console.log(values);
    setPersistedTestData(values);
    query.refetch();

    const v = getValues(formStore);
    console.log(v);
    // const result = callApi(
    //   values.endpoint as keyof API,
    //   JSON.parse(values.payload)
    // );
    // setResult(result);
  };
  return (
    <div class="p-2">
      <h1>API Tester</h1>
      <Form onSubmit={handleSubmit}>
        <div class="flex flex-col">
          <Field name="endpoint">
            {(field, fieldProps) => (
              <TextInput
                label={"endpoint"}
                value={field.value || ""}
                inputProps={fieldProps}
                formStore={formStore}
              />
            )}
          </Field>
          <Field name="payload">
            {(field, fieldProps) => (
              <TextInput
                label={"payload"}
                value={field.value || ""}
                inputProps={fieldProps}
                formStore={formStore}
              />
            )}
          </Field>
          <Button class="m-2" disabled={query.isFetching}>
            Send
          </Button>
        </div>
      </Form>
      <div>
        <Typography hierarchy="title" size="default">
          Result
        </Typography>
        <Switch>
          <Match when={query.isFetching}>
            <span>loading ...</span>
          </Match>
          <Match when={query.isFetched}>
            <pre>
              <code>{JSON.stringify(query.data, null, 2)}</code>
            </pre>
          </Match>
        </Switch>
      </div>
    </div>
  );
};
