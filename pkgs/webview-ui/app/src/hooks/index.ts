import { callApi } from "../api";
import { setActiveURI, setClanList } from "../App";

export const registerClan = async () => {
  try {
    const loc = await callApi("open_file", {
      file_request: { mode: "select_folder" },
    });
    if (loc.status === "success" && loc.data) {
      const data = loc.data[0];
      setClanList((s) => {
        const res = new Set([...s, data]);
        return Array.from(res);
      });
      setActiveURI(data);
      return data;
    }
  } catch (e) {
    //
  }
};
