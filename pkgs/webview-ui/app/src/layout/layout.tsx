import { Component, createEffect } from "solid-js";
import { Sidebar } from "@/src/components/Sidebar";
import { clanList } from "../App";
import { RouteSectionProps, useNavigate } from "@solidjs/router";

export const Layout: Component<RouteSectionProps> = (props) => {
  const navigate = useNavigate();
  createEffect(() => {
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
        <div class="drawer-content my-2 ml-8 overflow-x-hidden overflow-y-scroll rounded-lg border bg-def-1 border-def-3">
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
