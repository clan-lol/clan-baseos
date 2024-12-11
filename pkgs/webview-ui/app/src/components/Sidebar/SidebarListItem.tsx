import { A } from "@solidjs/router";

import { Typography } from "@/src/components/Typography";

interface SidebarListItem {
  title: string;
  href: string;
}

export const SidebarListItem = (props: SidebarListItem) => {
  const { title, href } = props;

  return (
    <li class="sidebar__list__item">
      <A class="sidebar__list__link" href={href}>
        <Typography
          class="sidebar__list__content"
          tag="span"
          hierarchy="body"
          size="s"
          weight="normal"
          color="primary"
          inverted={true}
        >
          {title}
        </Typography>
      </A>
    </li>
  );
};
