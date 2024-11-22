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
    <div class="h-screen w-full p-4 bg-def-3">
      <div class="drawer h-full lg:drawer-open ">
        <input
          id="toplevel-drawer"
          type="checkbox"
          class="drawer-toggle hidden"
        />
        <div class="drawer-content overflow-x-hidden overflow-y-scroll">
          <Show when={props.location.pathname !== "welcome"}>
            <Header clan_dir={activeURI} />
          </Show>
          {props.children}
        </div>
        <div
          class="drawer-side z-40 h-full min-w-72 rounded-xl border opacity-95 bg-inv-2 border-inv-2"
          classList={{
            "!hidden":
              props.location.pathname === "welcome" || clanList().length === 0,
          }}
        >
          <label
            for="toplevel-drawer"
            aria-label="close sidebar"
            class="drawer-overlay"
          ></label>
          <Sidebar {...props} />
        </div>
      </div>
    </div>
  );
};
