import { createQuery } from "@tanstack/solid-query";
import { callApi } from "../api";
import toast from "solid-toast";

export const createModulesQuery = (uri: string | null) =>
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
          return Object.entries(response.data);
        }
      }
      return [];
    },
  }));
