import { Component, createEffect, Show } from "solid-js";
import { Header } from "./header";
import { Sidebar } from "@/src/components/Sidebar";
import { activeURI, clanList } from "../App";
import { RouteSectionProps, useNavigate } from "@solidjs/router";

export const Layout: Component<RouteSectionProps> = (props) => {
  const navigate = useNavigate();
  createEffect(() => {
    console.log("Layout props", props.location);
    console.log(
      "empty ClanList, redirect to welcome page",
      clanList().length === 0,
    );
    if (clanList().length === 0) {
      navigate("/welcome");
    }
  });

  return (
    <div class="h-screen w-full p-4 bg-def-2">
      <div class="drawer h-full lg:drawer-open ">
        <input
          id="toplevel-drawer"
          type="checkbox"
          class="drawer-toggle hidden"
        />
        <div class="drawer-content overflow-x-hidden overflow-y-scroll p-2">
          <Show when={props.location.pathname !== "welcome"}>
            <Header clan_dir={activeURI} />
          </Show>
          {props.children}
        </div>
        <div
          class="drawer-side z-40 h-full !overflow-hidden"
          classList={{
            "!hidden":
              props.location.pathname === "welcome" || clanList().length === 0,
          }}
        >
          <label
            for="toplevel-drawer"
            aria-label="close sidebar"
            class="drawer-overlay !h-full !overflow-hidden "
          ></label>
          <Sidebar {...props} />
        </div>
      </div>
    </div>
  );
};
