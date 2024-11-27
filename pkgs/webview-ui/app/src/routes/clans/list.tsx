import { callApi } from "@/src/api";
import { activeURI, clanList, setActiveURI, setClanList } from "@/src/App";
import { createSignal, For, Match, Setter, Show, Switch } from "solid-js";
import { createQuery } from "@tanstack/solid-query";
import { useFloating } from "@/src/floating";
import { autoUpdate, flip, hide, offset, shift } from "@floating-ui/dom";
import { useNavigate, A } from "@solidjs/router";
import { registerClan } from "@/src/hooks";
import { Button } from "@/src/components/button";
import Icon from "@/src/components/icon";

interface ClanItemProps {
  clan_dir: string;
}
const ClanItem = (props: ClanItemProps) => {
  const { clan_dir } = props;

  const details = createQuery(() => ({
    queryKey: [clan_dir, "meta"],
    queryFn: async () => {
      const result = await callApi("show_clan_meta", { uri: clan_dir });
      if (result.status === "error") throw new Error("Failed to fetch data");
      return result.data;
    },
  }));
  const navigate = useNavigate();
  const [reference, setReference] = createSignal<HTMLElement>();
  const [floating, setFloating] = createSignal<HTMLElement>();

  // `position` is a reactive object.
  const position = useFloating(reference, floating, {
    placement: "top",

    // pass options. Ensure the cleanup function is returned.
    whileElementsMounted: (reference, floating, update) =>
      autoUpdate(reference, floating, update, {
        animationFrame: true,
      }),
    middleware: [
      offset(5),
      shift(),
      flip(),

      hide({
        strategy: "referenceHidden",
      }),
    ],
  });

  const handleRemove = () => {
    setClanList((s) =>
      s.filter((v, idx) => {
        if (v == clan_dir) {
          setActiveURI(clanList()[idx - 1] || clanList()[idx + 1] || null);
          return false;
        }
        return true;
      }),
    );
  };

  return (
    <div class="stat">
      <div class="stat-figure text-primary-800">
        <div class="join">
          <Button
            size="s"
            variant="light"
            class="join-item"
            onClick={() => navigate(`/clans/${window.btoa(clan_dir)}`)}
            endIcon={<Icon icon="Settings" />}
          ></Button>
          <Button
            size="s"
            variant="light"
            class="join-item "
            onClick={() => {
              setActiveURI(clan_dir);
            }}
          >
            {activeURI() === clan_dir ? "active" : "select"}
          </Button>
          <Button
            size="s"
            variant="light"
            popovertarget={`clan-delete-popover-${clan_dir}`}
            popovertargetaction="toggle"
            ref={setReference}
            class="btn btn-ghost btn-outline join-item"
            endIcon={<Icon icon="Trash" />}
          ></Button>
          <div
            popover="auto"
            role="tooltip"
            id={`clan-delete-popover-${clan_dir}`}
            ref={setFloating}
            style={{
              position: position.strategy,
              top: `${position.y ?? 0}px`,
              left: `${position.x ?? 0}px`,
            }}
            class="m-0 bg-transparent"
          >
            <Button
              size="s"
              onClick={handleRemove}
              variant="dark"
              endIcon={<Icon icon="Trash" />}
            >
              Remove from App
            </Button>
          </div>
        </div>
      </div>
      <div
        class="stat-title"
        classList={{
          "badge badge-primary": activeURI() === clan_dir,
        }}
      >
        {clan_dir}
      </div>

      <Show when={details.isLoading}>
        <div class="skeleton h-12 w-80" />
      </Show>
      <Show when={details.isSuccess}>
        <A href={`/clans/${window.btoa(clan_dir)}`}>
          <div class="stat-value underline">{details.data?.name}</div>
        </A>
      </Show>
      <Show when={details.isSuccess && details.data?.description}>
        <div class="stat-desc text-lg">{details.data?.description}</div>
      </Show>
    </div>
  );
};

export const ClanList = () => {
  const navigate = useNavigate();
  return (
    <div class="card card-normal">
      <div class="card-body">
        <div class="label">
          <div class="label-text text-2xl text-neutral">Registered Clans</div>
          <div class="flex gap-2">
            <span class="tooltip tooltip-top" data-tip="Register clan">
              <Button
                variant="light"
                onClick={registerClan}
                startIcon={<Icon icon="List" />}
              ></Button>
            </span>
            <span class="tooltip tooltip-top" data-tip="Create new clan">
              <Button
                onClick={() => {
                  navigate("create");
                }}
                startIcon={<Icon icon="Plus" />}
              ></Button>
            </span>
          </div>
        </div>
        <div class="stats stats-vertical shadow">
          <For each={clanList()}>
            {(value) => <ClanItem clan_dir={value} />}
          </For>
        </div>
      </div>
    </div>
  );
};
