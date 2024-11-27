import { createSignal, Show } from "solid-js";

import { Typography } from "@/src/components/Typography";
import { SidebarFlyout } from "./SidebarFlyout";

interface SidebarHeader {
  clanName: string;
}

export const SidebarHeader = (props: SidebarHeader) => {
  const { clanName } = props;

  const [showFlyout, toggleFlyout] = createSignal(false);

  function handleClick() {
    toggleFlyout(!showFlyout());
  }

  const renderClanProfile = () => (
    <div
      class={`sidebar__profile ${showFlyout() ? "sidebar__profile--flyout" : ""}`}
    >
      <Typography
        classes="sidebar__profile__character"
        tag="span"
        hierarchy="title"
        size="m"
        weight="bold"
        color="primary"
        inverted={true}
      >
        {clanName.slice(0, 1).toUpperCase()}
      </Typography>
    </div>
  );

  const renderClanTitle = () => (
    <Typography
      classes="sidebar__title"
      tag="h3"
      hierarchy="body"
      size="default"
      weight="medium"
      color="primary"
      inverted={true}
    >
      {clanName}
    </Typography>
  );

  return (
    <header class="sidebar__header">
      <div onClick={handleClick} class="sidebar__header__inner">
        {renderClanProfile()}
        {renderClanTitle()}
      </div>
      {showFlyout() && <SidebarFlyout />}
    </header>
  );
};
