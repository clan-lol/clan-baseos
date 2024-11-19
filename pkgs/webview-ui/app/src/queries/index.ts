import { createQuery } from "@tanstack/solid-query";
import { callApi } from "../api";
import toast from "solid-toast";

export interface ModulesFilter {
  features: string[];
}
export const createModulesQuery = (
  uri: string | null,
  filter?: ModulesFilter,
) =>
  createQuery(() => ({
    queryKey: [uri, "list_modules"],
    placeholderData: [],
    enabled: !!uri,
    queryFn: async () => {
      console.log({ uri });
      if (uri) {
        const response = await callApi("list_modules", {
          base_path: uri,
        });
        console.log({ response });
        if (response.status === "error") {
          toast.error("Failed to fetch data");
        } else {
          if (!filter) {
            return Object.entries(response.data);
          }
          return Object.entries(response.data).filter(([key, value]) =>
            filter.features.every((f) => (value.features || []).includes(f)),
          );
        }
      }
      return [];
    },
  }));
